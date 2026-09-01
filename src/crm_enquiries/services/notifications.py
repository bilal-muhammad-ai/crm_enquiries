"""Notification service for human approval requests."""

from __future__ import annotations

import logging

from crm_enquiries.config import get_settings
from crm_enquiries.services.email import get_email_provider

logger = logging.getLogger(__name__)


class NotificationService:
    async def notify_pending_approval(
        self,
        enquiry_id: str,
        flow_id: str,
        draft_subject: str,
        client_name: str,
        client_email: str,
    ) -> None:
        settings = get_settings()
        if not settings.approval_notify_email:
            logger.info(
                "Approval pending for enquiry %s (flow %s) — no APPROVAL_NOTIFY_EMAIL configured",
                enquiry_id,
                flow_id,
            )
            return

        body = (
            f"A new enquiry email draft requires your approval.\n\n"
            f"Enquiry ID: {enquiry_id}\n"
            f"Flow ID: {flow_id}\n"
            f"Client: {client_name} <{client_email}>\n"
            f"Subject: {draft_subject}\n\n"
            f"Review at: POST /api/v1/enquiries/{enquiry_id}/approve\n"
            f"View draft at: GET /api/v1/enquiries/{enquiry_id}/draft"
        )
        email = get_email_provider()
        await email.send(
            to=settings.approval_notify_email,
            subject=f"[Approval Required] Enquiry {enquiry_id}",
            body_plain=body,
        )
