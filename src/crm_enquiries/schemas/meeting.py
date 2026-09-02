"""Meeting analysis schemas."""

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    description: str
    owner: str = "Client Relationship Manager"
    due_hint: str | None = None


class MeetingAnalysis(BaseModel):
    meeting_summary: str
    client_requirements: list[str] = Field(default_factory=list)
    design_preferences: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    crm_status: str = "Brief Taken"
    crm_notes: str = ""
    suggested_follow_up_email: str | None = None


class ScheduleMeetingRequest(BaseModel):
    slot_start: str
    slot_end: str
    subject: str | None = None
    notes: str | None = None


class CalendarSlot(BaseModel):
    start: str
    end: str
    label: str
