from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    role: Mapped[UserRole] = mapped_column(nullable=False)
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schools.id"))
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    telegram_linked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    school = relationship("School", back_populates="members")
    teaching_assignments = relationship("TeacherClassAssignment", back_populates="teacher")
    student_enrollments = relationship("StudentEnrollment", back_populates="student")
    guardian_links_as_guardian = relationship("GuardianLink", foreign_keys="GuardianLink.guardian_id", back_populates="guardian")
    guardian_links_as_student = relationship("GuardianLink", foreign_keys="GuardianLink.student_id", back_populates="student")
