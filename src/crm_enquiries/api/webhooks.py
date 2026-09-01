"""Webhook endpoints."""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from crm_enquiries.database import async_session_factory, get_db
from crm_enquiries.flows.meeting_followup import MeetingFollowUpOrchestrator
from crm_enquiries.services.fathom import FathomService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


async def _process_fathom(payload: dict) -> None:
    async with async_session_factory() as session:
        orchestrator = MeetingFollowUpOrchestrator(session)
        await orchestrator.process_webhook(payload)
        await session.commit()


@router.post("/fathom", status_code=status.HTTP_202_ACCEPTED)
async def fathom_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await request.body()
    fathom = FathomService()

    webhook_id = request.headers.get("webhook-id", "")
    webhook_timestamp = request.headers.get("webhook-timestamp", "")
    webhook_signature = request.headers.get("webhook-signature", "")

    if fathom.settings.fathom_webhook_secret and not fathom.verify_webhook_signature(
        body, webhook_id, webhook_timestamp, webhook_signature
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    recording_id = payload.get("id") or payload.get("recording_id", "")

    if fathom.settings.fathom_mock:
        orchestrator = MeetingFollowUpOrchestrator(db)
        result = await orchestrator.process_webhook(payload)
        return {"status": "accepted", **result}

    background_tasks.add_task(_process_fathom, payload)
    return {"status": "accepted", "recording_id": recording_id}
