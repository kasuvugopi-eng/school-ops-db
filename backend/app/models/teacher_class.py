from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class TeacherClassAssignment(Base):
    __tablename__ = "teacher_class_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grade_classes.id"), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('teacher_id', 'class_id', name='uq_teacher_class'),
    )

    teacher = relationship("User", back_populates="teaching_assignments")
    grade_class = relationship("GradeClass", back_populates="teacher_assignments")
