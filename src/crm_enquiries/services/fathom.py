"""Fathom AI webhook and transcript service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any

import httpx

from crm_enquiries.config import get_settings

logger = logging.getLogger(__name__)


class FathomService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def verify_webhook_signature(
        self,
        body: bytes,
        webhook_id: str,
        webhook_timestamp: str,
        webhook_signature: str,
    ) -> bool:
        secret = self.settings.fathom_webhook_secret
        if not secret:
            return self.settings.fathom_mock

        signed_content = f"{webhook_id}.{webhook_timestamp}.{body.decode('utf-8')}"
        key = secret.encode("utf-8")
        if secret.startswith("whsec_"):
            try:
                key = base64.b64decode(secret[6:] + "==")
            except Exception:
                key = secret[6:].encode("utf-8")

        expected = hmac.new(key, signed_content.encode("utf-8"), hashlib.sha256).digest()
        expected_b64 = base64.b64encode(expected).decode("utf-8")

        for sig in webhook_signature.split(" "):
            if sig.startswith("v1,") and hmac.compare_digest(sig[3:], expected_b64):
                return True
        return False

    async def get_recording_details(self, recording_id: str) -> dict[str, Any]:
        if self.settings.fathom_mock:
            return {
                "id": recording_id,
                "title": "Glancy Fawcett Enquiry Brief Call",
                "summary": "Client discussed superyacht tableware requirements. Interested in showroom visit.",
                "transcript": (
                    "Client: We are outfitting a 60m superyacht and need luxury tableware.\n"
                    "GF: We would be delighted to arrange a brief-taking session at our Manchester showroom.\n"
                    "Client: We also need NDAs signed before sharing renders."
                ),
                "action_items": [
                    {"description": "Send NDA for signature", "assignee": "CRM Team"},
                    {"description": "Prepare superyacht product presentation", "assignee": "Project Manager"},
                ],
                "calendar_invitees": [{"email": "client@example.com", "name": "Client"}],
            }

        headers = {"X-Api-Key": self.settings.fathom_api_key}
        async with httpx.AsyncClient() as client:
            summary_resp = await client.get(
                f"https://api.fathom.ai/external/v1/recordings/{recording_id}/summary",
                headers=headers,
            )
            transcript_resp = await client.get(
                f"https://api.fathom.ai/external/v1/recordings/{recording_id}/transcript",
                headers=headers,
            )
            summary_resp.raise_for_status()
            transcript_resp.raise_for_status()
            return {
                "id": recording_id,
                "summary": summary_resp.json(),
                "transcript": transcript_resp.json(),
            }

    def extract_invitee_emails(self, payload: dict[str, Any]) -> list[str]:
        emails = []
        for invitee in payload.get("calendar_invitees", []):
            email = invitee.get("email")
            if email:
                emails.append(email.lower())
        return emails
