"""Human approval and scheduling endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.api.deps import verify_jwt_or_api_key
from crm_enquiries.database import get_db
from crm_enquiries.schemas.email_draft import ApprovalRequest, ApprovalResponse, EmailDraft
from crm_enquiries.schemas.meeting import ScheduleMeetingRequest
from crm_enquiries.services.enquiry_orchestrator import EnquiryOrchestrator

router = APIRouter(prefix="/api/v1/enquiries", tags=["approval"])


@router.get("/{enquiry_id}/draft", response_model=EmailDraft)
async def get_draft(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_jwt_or_api_key),
) -> EmailDraft:
    orchestrator = EnquiryOrchestrator(db)
    draft = await orchestrator.get_draft(enquiry_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/{enquiry_id}/availability")
async def get_availability(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_jwt_or_api_key),
) -> list[dict]:
    orchestrator = EnquiryOrchestrator(db)
    return await orchestrator.get_availability(enquiry_id)


@router.post("/{enquiry_id}/approve", response_model=ApprovalResponse)
async def approve_enquiry(
    enquiry_id: str,
    body: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_jwt_or_api_key),
) -> ApprovalResponse:
    orchestrator = EnquiryOrchestrator(db)
    try:
        enquiry = await orchestrator.approve_and_send(enquiry_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    messages = {
        "responded": "Email sent successfully.",
        "draft_pending": "Draft revised. Pending approval again.",
        "rejected": "Enquiry response rejected.",
        "meeting_scheduled": "Email sent and meeting scheduled.",
    }
    return ApprovalResponse(
        enquiry_id=enquiry.id,
        status=enquiry.status,
        message=messages.get(enquiry.status, f"Status updated to {enquiry.status}"),
    )


@router.post("/{enquiry_id}/schedule")
async def schedule_meeting(
    enquiry_id: str,
    body: ScheduleMeetingRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_jwt_or_api_key),
) -> dict:
    orchestrator = EnquiryOrchestrator(db)
    try:
        enquiry = await orchestrator.schedule_meeting(
            enquiry_id,
            body.slot_start,
            body.slot_end,
            body.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"enquiry_id": enquiry.id, "status": enquiry.status, "meeting_scheduled_at": body.slot_start}
