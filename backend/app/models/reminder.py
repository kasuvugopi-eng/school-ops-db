from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import ReminderType, ReminderState

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    target_student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reminder_type: Mapped[ReminderType] = mapped_column(nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(50), default="telegram")
    state: Mapped[ReminderState] = mapped_column(default=ReminderState.SCHEDULED)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    message_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment = relationship("Assignment")
    target_student = relationship("User")
