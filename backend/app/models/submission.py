from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import SubmissionState

class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    state: Mapped[SubmissionState] = mapped_column(default=SubmissionState.NOT_STARTED, nullable=False)
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    attachment_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("documents.id"))
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_student'),
    )

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User")
    attachment = relationship("Document")
    feedback_items = relationship("Feedback", back_populates="submission")
