"""Enquiry lifecycle orchestrator — intake through email send."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.config import get_settings
from crm_enquiries.crews.analysis.crew import run_analysis
from crm_enquiries.crews.response.crew import run_response_crew
from crm_enquiries.models.enquiry import Enquiry
from crm_enquiries.models.memory import FlowState
from crm_enquiries.providers.approval_feedback import ApprovalFeedbackProvider
from crm_enquiries.schemas.email_draft import ApprovalRequest, EmailDraft
from crm_enquiries.schemas.intake import EnquiryIntakeRequest
from crm_enquiries.services.calendar import get_calendar_provider
from crm_enquiries.services.email import get_email_provider
from crm_enquiries.services.memory_store import EnquiryMemoryStore
from crm_enquiries.services.notifications import NotificationService
from crm_enquiries.services.suitecrm import SuiteCRMService

logger = logging.getLogger(__name__)


class EnquiryOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.memory = EnquiryMemoryStore(session)
        self.crm = SuiteCRMService()
        self.approval_provider = ApprovalFeedbackProvider()
        self.notifications = NotificationService()
        self.settings = get_settings()

    async def start_enquiry(self, intake: EnquiryIntakeRequest) -> Enquiry:
        enquiry = Enquiry(
            name=intake.name,
            email=str(intake.email),
            phone=intake.phone,
            enquiry_type=intake.enquiry_type.value,
            message=intake.message,
            company=intake.company,
            status="new",
        )
        self.session.add(enquiry)
        await self.session.flush()

        await self.memory.append(enquiry.id, "intake", intake.model_dump(mode="json"))

        crm_id = await self.crm.create_enquiry(intake)
        enquiry.crm_id = crm_id
        enquiry.status = "crm_created"
        await self.memory.append(enquiry.id, "crm_created", {"crm_id": crm_id})

        history = await self.memory.get_history_summary(enquiry.id)
        use_llm = bool(self.settings.groq_api_key or self.settings.openai_api_key)
        analysis = run_analysis(
            {
                "name": intake.name,
                "email": str(intake.email),
                "company": intake.company or "Not provided",
                "enquiry_type": intake.enquiry_type.value,
                "message": intake.message,
                "enquiry_history": history,
            },
            use_llm=use_llm,
        )
        enquiry.analysis = analysis.model_dump()
        enquiry.status = "classified"
        await self.crm.update_from_analysis(crm_id, analysis)
        await self.memory.append(enquiry.id, "classified", analysis.model_dump())

        draft = run_response_crew(
            {
                "name": intake.name,
                "email": str(intake.email),
                "enquiry_type": intake.enquiry_type.value,
                "message": intake.message,
                "internal_summary": analysis.internal_summary,
                "intent_tags": analysis.intent_tags,
                "enquiry_history": history,
            },
            use_llm=use_llm,
        )
        enquiry.email_draft = draft.model_dump()
        enquiry.status = "draft_pending"

        flow_id = str(uuid.uuid4())
        enquiry.flow_id = flow_id
        flow_state = self.approval_provider.create_pending_state(
            enquiry_id=enquiry.id,
            flow_name="EnquiryLifecycleFlow",
            pending_step="draft_email",
            context={"enquiry_id": enquiry.id, "flow_id": flow_id},
            draft_snapshot=draft.model_dump(),
        )
        self.session.add(flow_state)
        await self.crm.update_status(crm_id, "draft_pending")
        await self.memory.append(enquiry.id, "draft_created", draft.model_dump())

        await self.notifications.notify_pending_approval(
            enquiry_id=enquiry.id,
            flow_id=flow_id,
            draft_subject=draft.subject,
            client_name=intake.name,
            client_email=str(intake.email),
        )

        await self.session.flush()
        return enquiry

    async def get_draft(self, enquiry_id: str) -> EmailDraft | None:
        enquiry = await self._get_enquiry(enquiry_id)
        if not enquiry or not enquiry.email_draft:
            return None
        return EmailDraft(**enquiry.email_draft)

    async def get_availability(self, enquiry_id: str) -> list[dict]:
        calendar = get_calendar_provider()
        slots = await calendar.get_availability(count=5)
        enquiry = await self._get_enquiry(enquiry_id)
        if enquiry:
            await self.memory.append(
                enquiry_id,
                "availability_fetched",
                {"slots": [s.model_dump() for s in slots]},
            )
        return [s.model_dump() for s in slots]

    async def approve_and_send(self, enquiry_id: str, approval: ApprovalRequest) -> Enquiry:
        enquiry = await self._get_enquiry(enquiry_id)
        if not enquiry:
            raise ValueError(f"Enquiry {enquiry_id} not found")

        draft = EmailDraft(**(enquiry.email_draft or {}))
        if approval.edited_subject:
            draft.subject = approval.edited_subject
        if approval.edited_body_plain:
            draft.body_plain = approval.edited_body_plain
            draft.body_html = approval.edited_body_plain.replace("\n", "<br>\n")

        if approval.action == "rejected":
            enquiry.status = "rejected"
            await self.memory.append(enquiry_id, "rejected", {"feedback": approval.feedback})
            if enquiry.crm_id:
                await self.crm.update_status(enquiry.crm_id, "closed")
            await self.session.flush()
            return enquiry

        if approval.action == "revise":
            use_llm = bool(self.settings.groq_api_key or self.settings.openai_api_key)
            revised = run_response_crew(
                {
                    "name": enquiry.name,
                    "email": enquiry.email,
                    "enquiry_type": enquiry.enquiry_type,
                    "message": enquiry.message,
                    "internal_summary": (enquiry.analysis or {}).get("internal_summary", ""),
                    "intent_tags": (enquiry.analysis or {}).get("intent_tags", []),
                    "enquiry_history": await self.memory.get_history_summary(enquiry_id),
                    "revision_feedback": approval.feedback,
                },
                use_llm=use_llm,
            )
            enquiry.email_draft = revised.model_dump()
            enquiry.status = "draft_pending"
            await self.memory.append(enquiry_id, "draft_revised", revised.model_dump())
            await self.session.flush()
            return enquiry

        calendar_slots = []
        if approval.schedule_meeting or draft.suggested_meeting:
            calendar = get_calendar_provider()
            slots = await calendar.get_availability(count=5)
            calendar_slots = [s.model_dump() for s in slots]

        body_plain = draft.body_plain
        if calendar_slots and not approval.selected_slot:
            slot_lines = "\n".join(f"  - {s['label']}" for s in calendar_slots[:5])
            body_plain += f"\n\nWe have the following availability for a brief-taking session:\n{slot_lines}\n\nPlease let us know which time suits you best."
        elif approval.selected_slot:
            body_plain += f"\n\nWe have scheduled a meeting for: {approval.selected_slot}"

        email_provider = get_email_provider()
        await email_provider.send(
            to=enquiry.email,
            subject=draft.subject,
            body_plain=body_plain,
            body_html=body_plain.replace("\n", "<br>\n"),
        )
        enquiry.status = "responded"
        await self.memory.append(enquiry_id, "approved", {"feedback": approval.feedback})
        await self.memory.append(enquiry_id, "email_sent", {"subject": draft.subject, "to": enquiry.email})

        if enquiry.crm_id:
            await self.crm.update_status(enquiry.crm_id, "responded")

        if approval.schedule_meeting and approval.selected_slot:
            await self._schedule_meeting(enquiry, approval.selected_slot, draft)

        await self.session.flush()
        return enquiry

    async def schedule_meeting(
        self,
        enquiry_id: str,
        slot_start: str,
        slot_end: str,
        subject: str | None = None,
    ) -> Enquiry:
        enquiry = await self._get_enquiry(enquiry_id)
        if not enquiry:
            raise ValueError(f"Enquiry {enquiry_id} not found")

        draft = enquiry.email_draft or {}
        meeting_subject = subject or draft.get("subject", "Glancy Fawcett — Project Brief")
        calendar = get_calendar_provider()
        event = await calendar.create_event(
            subject=meeting_subject,
            start=slot_start,
            end=slot_end,
            attendee_email=enquiry.email,
            body=enquiry.message,
        )

        if enquiry.crm_id:
            meeting_id = await self.crm.create_meeting(
                enquiry.crm_id,
                meeting_subject,
                slot_start,
                slot_end,
                enquiry.email,
            )
            await self.crm.set_fathom_recording(enquiry.crm_id, "", slot_start)

        enquiry.meeting_scheduled_at = slot_start  # type: ignore[assignment]
        enquiry.status = "meeting_scheduled"
        enquiry.state = {**enquiry.state, "calendar_event": event}
        await self.memory.append(enquiry_id, "meeting_scheduled", {"slot_start": slot_start, "slot_end": slot_end})
        await self.session.flush()
        return enquiry

    async def _schedule_meeting(self, enquiry: Enquiry, selected_slot: str, draft: EmailDraft) -> None:
        calendar = get_calendar_provider()
        slots = await calendar.get_availability(count=5)
        matched = next((s for s in slots if s.start == selected_slot or s.label == selected_slot), None)
        if matched:
            await self.schedule_meeting(enquiry.id, matched.start, matched.end, draft.subject)

    async def _get_enquiry(self, enquiry_id: str) -> Enquiry | None:
        from sqlalchemy import select

        result = await self.session.execute(select(Enquiry).where(Enquiry.id == enquiry_id))
        return result.scalar_one_or_none()
