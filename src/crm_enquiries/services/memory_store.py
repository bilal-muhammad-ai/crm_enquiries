"""Enquiry memory store — append-only events and history summaries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.models.enquiry import Enquiry
from crm_enquiries.models.memory import EnquiryMemoryEvent


class EnquiryMemoryStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        enquiry_id: str,
        event_type: str,
        payload: dict | None = None,
    ) -> EnquiryMemoryEvent:
        event = EnquiryMemoryEvent(
            enquiry_id=enquiry_id,
            event_type=event_type,
            payload=payload or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_timeline(self, enquiry_id: str) -> list[dict]:
        result = await self.session.execute(
            select(EnquiryMemoryEvent)
            .where(EnquiryMemoryEvent.enquiry_id == enquiry_id)
            .order_by(EnquiryMemoryEvent.created_at)
        )
        events = result.scalars().all()
        return [
            {
                "event_type": e.event_type,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

    async def get_history_summary(self, enquiry_id: str, limit: int = 20) -> str:
        timeline = await self.get_timeline(enquiry_id)
        if not timeline:
            return "No prior history for this enquiry."
        recent = timeline[-limit:]
        lines = []
        for item in recent:
            lines.append(f"- [{item['event_type']}] {item.get('created_at', '')}: {item.get('payload', {})}")
        return "\n".join(lines)

    async def update_enquiry_state(
        self,
        enquiry: Enquiry,
        status: str | None = None,
        state_patch: dict | None = None,
    ) -> Enquiry:
        if status:
            enquiry.status = status
        if state_patch:
            enquiry.state = {**enquiry.state, **state_patch}
        await self.session.flush()
        return enquiry
