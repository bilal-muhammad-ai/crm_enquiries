"""Pydantic schemas for enquiry intake."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EnquiryType(str, Enum):
    SUPERyACHT = "superyacht"
    RESIDENTIAL = "residential"
    AIRCRAFT = "aircraft"
    GENERAL = "general"


class EnquiryIntakeRequest(BaseModel):
    """Core enquiry fields — terms/newsletter are ignored if present."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    enquiry_type: EnquiryType
    message: str = Field(..., min_length=1)
    company: str | None = Field(default=None, max_length=255)


class EnquiryIntakeResponse(BaseModel):
    enquiry_id: str
    status: str
    message: str = "Enquiry received and processing started"


class EnquiryStatusResponse(BaseModel):
    enquiry_id: str
    status: str
    crm_id: str | None = None
    flow_id: str | None = None
    timeline: list[dict] = Field(default_factory=list)
    state: dict = Field(default_factory=dict)
