"""Enquiry intake and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.api.deps import verify_api_key
from crm_enquiries.database import get_db
from crm_enquiries.schemas.intake import EnquiryIntakeRequest, EnquiryIntakeResponse, EnquiryStatusResponse
from crm_enquiries.services.enquiry_orchestrator import EnquiryOrchestrator
from crm_enquiries.services.memory_store import EnquiryMemoryStore

router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])


@router.post("", response_model=EnquiryIntakeResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_enquiry(
    intake: EnquiryIntakeRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
) -> EnquiryIntakeResponse:
    """Receive enquiry form submission and start processing flow."""
    orchestrator = EnquiryOrchestrator(db)
    enquiry = await orchestrator.start_enquiry(intake)
    return EnquiryIntakeResponse(
        enquiry_id=enquiry.id,
        status=enquiry.status,
        message="Enquiry received. Email draft pending human approval.",
    )


@router.get("/{enquiry_id}", response_model=EnquiryStatusResponse)
async def get_enquiry(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
) -> EnquiryStatusResponse:
    orchestrator = EnquiryOrchestrator(db)
    enquiry = await orchestrator._get_enquiry(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    memory = EnquiryMemoryStore(db)
    timeline = await memory.get_timeline(enquiry_id)

    return EnquiryStatusResponse(
        enquiry_id=enquiry.id,
        status=enquiry.status,
        crm_id=enquiry.crm_id,
        flow_id=enquiry.flow_id,
        timeline=timeline,
        state={
            "analysis": enquiry.analysis,
            "email_draft": enquiry.email_draft,
            "meeting_analysis": enquiry.meeting_analysis,
            **enquiry.state,
        },
    )
