"""Meeting follow-up flow — Fathom transcript to CRM update."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.config import get_settings
from crm_enquiries.crews.meeting.crew import run_meeting_analysis
from crm_enquiries.models.enquiry import Enquiry
from crm_enquiries.services.fathom import FathomService
from crm_enquiries.services.memory_store import EnquiryMemoryStore
from crm_enquiries.services.suitecrm import SuiteCRMService

logger = logging.getLogger(__name__)


class MeetingFollowUpOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.memory = EnquiryMemoryStore(session)
        self.fathom = FathomService()
        self.crm = SuiteCRMService()
        self.settings = get_settings()

    async def process_webhook(self, payload: dict) -> dict:
        recording_id = payload.get("id") or payload.get("recording_id", "")
        if not recording_id:
            raise ValueError("Missing recording id in Fathom payload")

        details = await self.fathom.get_recording_details(recording_id)
        summary = details.get("summary", "")
        if isinstance(summary, dict):
            summary = summary.get("markdown_formatted", str(summary))
        transcript = details.get("transcript", "")
        if isinstance(transcript, dict):
            transcript = transcript.get("text", str(transcript))

        invitee_emails = self.fathom.extract_invitee_emails(payload) or self.fathom.extract_invitee_emails(details)
        enquiry = await self._match_enquiry(invitee_emails, recording_id)

        await self.memory.append(
            enquiry.id if enquiry else "unknown",
            "transcript_received",
            {"recording_id": recording_id, "invitee_emails": invitee_emails},
        )

        if not enquiry:
            logger.warning("No enquiry matched for Fathom recording %s", recording_id)
            return {"status": "no_match", "recording_id": recording_id}

        history = await self.memory.get_history_summary(enquiry.id)
        use_llm = bool(self.settings.groq_api_key or self.settings.openai_api_key)
        analysis = await run_meeting_analysis(
            {
                "summary": summary,
                "transcript": transcript,
                "enquiry_history": history,
                "client_name": enquiry.name,
                "enquiry_type": enquiry.enquiry_type,
            },
            use_llm=use_llm,
        )

        enquiry.meeting_analysis = analysis.model_dump()
        enquiry.fathom_recording_id = recording_id
        enquiry.status = "brief_taken"

        if enquiry.crm_id:
            await self.crm.update_from_meeting(enquiry.crm_id, analysis)
            await self.crm.set_fathom_recording(enquiry.crm_id, recording_id, payload.get("recording_start_time", ""))

        await self.memory.append(enquiry.id, "crm_updated", analysis.model_dump())
        await self.session.flush()

        return {
            "status": "processed",
            "enquiry_id": enquiry.id,
            "recording_id": recording_id,
            "crm_status": analysis.crm_status,
        }

    async def _match_enquiry(self, emails: list[str], recording_id: str) -> Enquiry | None:
        if recording_id:
            result = await self.session.execute(
                select(Enquiry).where(Enquiry.fathom_recording_id == recording_id)
            )
            enquiry = result.scalar_one_or_none()
            if enquiry:
                return enquiry

        for email in emails:
            result = await self.session.execute(
                select(Enquiry).where(Enquiry.email == email).order_by(Enquiry.created_at.desc())
            )
            enquiry = result.scalars().first()
            if enquiry:
                return enquiry

        for email in emails:
            crm_id = await self.crm.find_enquiry_by_email(email)
            if crm_id:
                result = await self.session.execute(select(Enquiry).where(Enquiry.crm_id == crm_id))
                enquiry = result.scalar_one_or_none()
                if enquiry:
                    return enquiry
        return None
