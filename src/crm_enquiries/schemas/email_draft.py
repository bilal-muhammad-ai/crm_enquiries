"""Email draft schemas."""

from pydantic import BaseModel, Field


class EmailDraft(BaseModel):
    subject: str
    body_html: str
    body_plain: str
    kb_citations: list[str] = Field(default_factory=list)
    suggested_meeting: bool = False
    meeting_context: str | None = None
    validation_passed: bool = True
    validation_issues: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    flow_id: str
    action: str = Field(..., pattern="^(approved|rejected|revise)$")
    feedback: str = ""
    edited_subject: str | None = None
    edited_body_plain: str | None = None
    schedule_meeting: bool = False
    selected_slot: str | None = None


class ApprovalResponse(BaseModel):
    enquiry_id: str
    status: str
    message: str
