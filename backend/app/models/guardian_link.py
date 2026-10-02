from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class GuardianLink(Base):
    __tablename__ = "guardian_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column("relationship", String(50), default="parent")
    opted_in: Mapped[bool] = mapped_column(Boolean, default=False)
    opted_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('guardian_id', 'student_id', name='uq_guardian_student'),
    )

    guardian = relationship("User", foreign_keys=[guardian_id], back_populates="guardian_links_as_guardian")
    student = relationship("User", foreign_keys=[student_id], back_populates="guardian_links_as_student")
