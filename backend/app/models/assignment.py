from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import AssignmentState, AssignmentTargetType

class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    target_type: Mapped[AssignmentTargetType] = mapped_column(nullable=False)
    target_class_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("grade_classes.id"))
    target_student_ids: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[AssignmentState] = mapped_column(default=AssignmentState.DRAFT, nullable=False)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    school = relationship("School", back_populates="assignments")
    creator = relationship("User")
    target_class = relationship("GradeClass")
    source_document = relationship("Document", foreign_keys=[source_document_id])
    submissions = relationship("Submission", back_populates="assignment")
