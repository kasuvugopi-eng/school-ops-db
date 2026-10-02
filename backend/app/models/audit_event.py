from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    correlation_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schools.id"))
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    actor_type: Mapped[Optional[str]] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column()
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
