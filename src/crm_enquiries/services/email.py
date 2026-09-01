"""Email provider — abstract + M365 Graph implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from crm_enquiries.config import get_settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        body_plain: str,
        body_html: str | None = None,
    ) -> dict:
        pass


class MockEmailProvider(EmailProvider):
    async def send(
        self,
        to: str,
        subject: str,
        body_plain: str,
        body_html: str | None = None,
    ) -> dict:
        logger.info("Mock email sent to %s: %s", to, subject)
        return {"status": "sent", "to": to, "subject": subject, "mock": True}


class M365EmailProvider(EmailProvider):
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

    async def send(
        self,
        to: str,
        subject: str,
        body_plain: str,
        body_html: str | None = None,
    ) -> dict:
        token = await self._get_token()
        content_type = "HTML" if body_html else "Text"
        content = body_html or body_plain
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": content_type, "content": content},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": True,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.microsoft.com/v1.0/users/{self.settings.outbound_from_email}/sendMail",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            resp.raise_for_status()
        return {"status": "sent", "to": to, "subject": subject}


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    if settings.email_mock:
        return MockEmailProvider()
    return M365EmailProvider()
