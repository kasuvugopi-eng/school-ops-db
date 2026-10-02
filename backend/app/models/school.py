from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class School(Base):
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    policy_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    members = relationship("User", back_populates="school")
    grade_classes = relationship("GradeClass", back_populates="school")
    assignments = relationship("Assignment", back_populates="school")
