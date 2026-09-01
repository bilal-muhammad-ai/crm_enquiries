"""Calendar provider — abstract + M365 Graph implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import httpx

from crm_enquiries.config import get_settings
from crm_enquiries.schemas.meeting import CalendarSlot

logger = logging.getLogger(__name__)


class CalendarProvider(ABC):
    @abstractmethod
    async def get_availability(self, count: int = 5) -> list[CalendarSlot]:
        pass

    @abstractmethod
    async def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        attendee_email: str,
        body: str = "",
    ) -> dict:
        pass


class MockCalendarProvider(CalendarProvider):
    async def get_availability(self, count: int = 5) -> list[CalendarSlot]:
        settings = get_settings()
        slots: list[CalendarSlot] = []
        base = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        for i in range(count):
            start = base + timedelta(days=i + 1)
            end = start + timedelta(minutes=settings.default_meeting_duration_minutes)
            slots.append(
                CalendarSlot(
                    start=start.isoformat(),
                    end=end.isoformat(),
                    label=start.strftime("%A %d %B %Y at %H:%M UTC"),
                )
            )
        return slots

    async def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        attendee_email: str,
        body: str = "",
    ) -> dict:
        logger.info("Mock calendar event: %s with %s (%s - %s)", subject, attendee_email, start, end)
        return {
            "status": "scheduled",
            "subject": subject,
            "start": start,
            "end": end,
            "attendee": attendee_email,
            "mock": True,
        }


class M365CalendarProvider(CalendarProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{self.settings.m365_tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": self.settings.m365_client_id,
                    "client_secret": self.settings.m365_client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    async def get_availability(self, count: int = 5) -> list[CalendarSlot]:
        token = await self._get_token()
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=self.settings.availability_lookahead_days)
        payload = {
            "schedules": [self.settings.calendar_user_email or self.settings.outbound_from_email],
            "startTime": {"dateTime": now.isoformat(), "timeZone": "UTC"},
            "endTime": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "availabilityViewInterval": self.settings.default_meeting_duration_minutes,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://graph.microsoft.com/v1.0/me/calendar/getSchedule",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        slots: list[CalendarSlot] = []
        for schedule in data.get("value", []):
            for item in schedule.get("scheduleItems", []):
                if item.get("status") == "free" and len(slots) < count:
                    start = item["start"]["dateTime"]
                    end_time = item["end"]["dateTime"]
                    slots.append(
                        CalendarSlot(
                            start=start,
                            end=end_time,
                            label=f"{start} - {end_time}",
                        )
                    )
        if not slots:
            return await MockCalendarProvider().get_availability(count)
        return slots

    async def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        attendee_email: str,
        body: str = "",
    ) -> dict:
        token = await self._get_token()
        user = self.settings.calendar_user_email or self.settings.outbound_from_email
        payload = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
            "attendees": [
                {
                    "emailAddress": {"address": attendee_email},
                    "type": "required",
                }
            ],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.microsoft.com/v1.0/users/{user}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


def get_calendar_provider() -> CalendarProvider:
    settings = get_settings()
    if settings.calendar_mock:
        return MockCalendarProvider()
    return M365CalendarProvider()
