from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class GradeClass(Base):
    __tablename__ = "grade_classes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade_level: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    school = relationship("School", back_populates="grade_classes")
    teacher_assignments = relationship("TeacherClassAssignment", back_populates="grade_class")
    student_enrollments = relationship("StudentEnrollment", back_populates="grade_class")
