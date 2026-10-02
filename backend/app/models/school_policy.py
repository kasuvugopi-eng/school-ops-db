from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import PolicyType

class SchoolPolicy(Base):
    __tablename__ = "school_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    policy_type: Mapped[PolicyType] = mapped_column(nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("documents.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    school = relationship("School")
    source_document = relationship("Document")
