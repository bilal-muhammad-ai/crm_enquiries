"""SuiteCRM REST API service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from crm_enquiries.config import get_settings, load_crm_field_map
from crm_enquiries.schemas.analysis import EnquiryAnalysis
from crm_enquiries.schemas.intake import EnquiryIntakeRequest
from crm_enquiries.schemas.meeting import MeetingAnalysis

logger = logging.getLogger(__name__)


class SuiteCRMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.field_map = load_crm_field_map()
        self._token: str | None = None
        self._mock_records: dict[str, dict] = {}

    @property
    def module(self) -> str:
        return self.field_map.get("module", "Leads")

    def _crm_field(self, key: str) -> str:
        return self.field_map.get("fields", {}).get(key, key)

    def _enquiry_type_label(self, enquiry_type: str) -> str:
        return self.field_map.get("enquiry_type_values", {}).get(enquiry_type, enquiry_type)

    async def _get_token(self) -> str:
        if self.settings.suitecrm_mock:
            return "mock-token"
        if self._token:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.settings.suitecrm_base_url}/Api/access_token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.suitecrm_client_id,
                    "client_secret": self.settings.suitecrm_client_secret,
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if self.settings.suitecrm_mock:
            return {}
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            logger.info("Requesting %s %s with token %s", method, path, token)
            resp = await client.request(
                method,
                f"{self.settings.suitecrm_base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    def _parse_name(self, full_name: str) -> tuple[str, str]:
        parts = full_name.strip().split(None, 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    async def create_enquiry(self, intake: EnquiryIntakeRequest) -> str:
        first, last = self._parse_name(intake.name)
        type_label = self._enquiry_type_label(intake.enquiry_type.value)
        record_name = f"{intake.name} — {type_label}"

        payload = {
            self._crm_field("name"): record_name,
            self._crm_field("email"): str(intake.email),
            self._crm_field("phone"): intake.phone or "",
            self._crm_field("enquiry_type"): type_label,
            self._crm_field("message"): intake.message,
            self._crm_field("status"): self.field_map.get("status_values", {}).get("new", "New"),
        }

        if self.settings.suitecrm_mock:
            crm_id = str(uuid.uuid4())
            self._mock_records[crm_id] = {
                **payload,
                "contact": {"first_name": first, "last_name": last, "email": str(intake.email)},
                "company": intake.company,
            }
            logger.info("Mock CRM enquiry created: %s", crm_id)
            return crm_id

        #contact_id = await self._find_or_create_contact(first, last, str(intake.email), intake.phone)
        data: dict[str, Any] = {"data": {"type": self.module, "attributes": payload}}
        #if contact_id:
        #    data["data"]["attributes"]["contact_id"] = contact_id
        #if intake.company:
        #    account_id = await self._find_or_create_account(intake.company)
        #    if account_id:
        #        data["data"]["attributes"]["account_id"] = account_id
        logger.info("Creating CRM enquiry: %s", data)
        result = await self._request("POST", f"/Api/V8/module", json=data)
        return result.get("data", {}).get("id", str(uuid.uuid4()))

    async def _find_or_create_contact(
        self, first: str, last: str, email: str, phone: str | None
    ) -> str | None:
        if self.settings.suitecrm_mock:
            return str(uuid.uuid4())
        try:
            result = await self._request(
                "GET",
                "/Api/V8/module/Contacts",
                params={"filter[email1][eq]": email},
            )
            records = result.get("data", [])
            if records:
                return records[0]["id"]
            create = await self._request(
                "POST",
                "/Api/V8/module",
                json={
                    "data": {
                        "type": "Contacts",
                        "attributes": {
                            "first_name": first,
                            "last_name": last or first,
                            "email1": email,
                            "phone_work": phone or "",
                        },
                    }
                },
            )
            return create.get("data", {}).get("id")
        except Exception as exc:
            logger.warning("Contact create/find failed: %s", exc)
            return None

    async def _find_or_create_account(self, company: str) -> str | None:
        if self.settings.suitecrm_mock:
            return str(uuid.uuid4())
        try:
            result = await self._request(
                "GET",
                "/Api/V8/module/Accounts",
                params={"filter[name][eq]": company},
            )
            records = result.get("data", [])
            if records:
                return records[0]["id"]
            create = await self._request(
                "POST",
                "/Api/V8/module",
                json={"data": {"type": "Accounts", "attributes": {"name": company}}},
            )
            return create.get("data", {}).get("id")
        except Exception as exc:
            logger.warning("Account create/find failed: %s", exc)
            return None

    async def update_from_analysis(self, crm_id: str, analysis: EnquiryAnalysis) -> None:
        updates = {
            #self._crm_field("priority"): analysis.priority,
            #self._crm_field("classification_tags"): ",".join(analysis.intent_tags),
            #self._crm_field("internal_summary"): analysis.internal_summary,
            self._crm_field("status"): self.field_map.get("status_values", {}).get("classified", "Classified"),
            **analysis.crm_field_updates,
        }
        await self._update_record(crm_id, updates)

    async def update_status(self, crm_id: str, status_key: str) -> None:
        status = self.field_map.get("status_values", {}).get(status_key, status_key)
        await self._update_record(crm_id, {self._crm_field("status"): status})

    async def update_from_meeting(self, crm_id: str, analysis: MeetingAnalysis) -> None:
        updates = {
            self._crm_field("status"): analysis.crm_status,
            self._crm_field("internal_summary"): analysis.crm_notes,
        }
        await self._update_record(crm_id, updates)

    async def create_meeting(
        self,
        crm_id: str,
        subject: str,
        start: str,
        end: str,
        invitee_email: str,
        notes: str = "",
    ) -> str:
        if self.settings.suitecrm_mock:
            meeting_id = str(uuid.uuid4())
            logger.info("Mock CRM meeting created: %s for enquiry %s", meeting_id, crm_id)
            return meeting_id

        result = await self._request(
            "POST",
            "/Api/V8/module",
            json={
                "data": {
                    "type": "Meetings",
                    "attributes": {
                        "name": subject,
                        "date_start": start,
                        "date_end": end,
                        "description": notes,
                        "parent_type": self.module,
                        "parent_id": crm_id,
                        "invitees": invitee_email,
                    },
                }
            },
        )
        return result.get("data", {}).get("id", str(uuid.uuid4()))

    async def set_fathom_recording(self, crm_id: str, recording_id: str, scheduled_at: str) -> None:
        await self._update_record(
            crm_id,
            {
                self._crm_field("fathom_recording_id"): recording_id,
                self._crm_field("meeting_scheduled_at"): scheduled_at,
            },
        )

    async def find_enquiry_by_email(self, email: str) -> str | None:
        if self.settings.suitecrm_mock:
            for crm_id, record in self._mock_records.items():
                if record.get(self._crm_field("email")) == email:
                    return crm_id
            return None
        try:
            result = await self._request(
                "GET",
                f"/Api/V8/module/{self.module}",
                params={"filter[email1][eq]": email, "sort": "-date_entered", "page[size]": 1},
            )
            records = result.get("data", [])
            return records[0]["id"] if records else None
        except Exception as exc:
            logger.warning("Enquiry lookup failed: %s", exc)
            return None

    async def _update_record(self, crm_id: str, attributes: dict[str, Any]) -> None:
        if self.settings.suitecrm_mock:
            if crm_id in self._mock_records:
                self._mock_records[crm_id].update(attributes)
            logger.info("Mock CRM update %s: %s", crm_id, attributes)
            return
        logger.info("Updating CRM record %s: %s", crm_id, attributes)
        await self._request(
            "PATCH",
            "/Api/V8/module",
            json={"data": {"type": self.module, "id": crm_id, "attributes": attributes}},
        )
