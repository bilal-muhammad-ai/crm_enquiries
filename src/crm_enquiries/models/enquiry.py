"""Enquiry SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_enquiries.database import Base


class Enquiry(Base):
    __tablename__ = "enquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enquiry_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    crm_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flow_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    state: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    email_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meeting_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    fathom_recording_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meeting_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
