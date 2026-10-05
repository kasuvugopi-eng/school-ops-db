import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_class_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("grade_classes.id"), nullable=True) # Null = All Classes
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # ALL, STUDENT, TEACHER, GUARDIAN
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school = relationship("School")
    author = relationship("User", foreign_keys=[created_by])
    target_class = relationship("GradeClass", foreign_keys=[target_class_id])
