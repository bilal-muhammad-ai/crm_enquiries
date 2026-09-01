"""Approval feedback provider for human-in-the-loop."""

from __future__ import annotations

import uuid

from crm_enquiries.models.memory import FlowState


class ApprovalFeedbackProvider:
    """Pauses flow execution and persists state for async human approval."""

    def create_pending_state(
        self,
        enquiry_id: str,
        flow_name: str,
        pending_step: str,
        context: dict,
        draft_snapshot: dict | None = None,
    ) -> FlowState:
        return FlowState(
            id=str(uuid.uuid4()),
            enquiry_id=enquiry_id,
            flow_name=flow_name,
            status="pending_approval",
            pending_step=pending_step,
            context=context,
            draft_snapshot=draft_snapshot,
        )

    def build_feedback_payload(self, action: str, feedback: str = "") -> str:
        return f"{action}|{feedback}"

    def parse_feedback(self, payload: str) -> tuple[str, str]:
        if "|" in payload:
            action, feedback = payload.split("|", 1)
            return action.strip(), feedback.strip()
        return payload.strip(), ""
