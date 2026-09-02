"""Analysis crew output schemas."""

from typing import Any

from pydantic import BaseModel, Field

from crm_enquiries.schemas.intake import EnquiryType


class EnquiryAnalysis(BaseModel):
    enquiry_type: EnquiryType
    priority: int = Field(ge=1, le=5)
    intent_tags: list[str] = Field(default_factory=list)
    suggested_assignee_role: str = "Client Relationship Manager"
    internal_summary: str
    type_contradiction: bool = False
    type_contradiction_note: str | None = None
    crm_field_updates: dict[str, Any] = Field(default_factory=dict)
