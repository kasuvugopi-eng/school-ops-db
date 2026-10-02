from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import ParseApprovalState

class DocumentParseResult(Base):
    __tablename__ = "document_parse_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    parsed_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_notes: Mapped[dict] = mapped_column(JSON, default=dict)
    ambiguity_flags: Mapped[list] = mapped_column(JSON, default=list)
    approval_state: Mapped[ParseApprovalState] = mapped_column(default=ParseApprovalState.PENDING)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    clarification_question: Mapped[Optional[str]] = mapped_column(Text)
    clarification_response: Mapped[Optional[str]] = mapped_column(Text)
    model_used: Mapped[Optional[str]] = mapped_column(String(100))
    raw_model_response: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="parse_results")
    approver = relationship("User")
