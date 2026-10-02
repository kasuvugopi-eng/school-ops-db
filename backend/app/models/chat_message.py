from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_chat_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    detected_intent: Mapped[Optional[str]] = mapped_column(String(100))
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float)
    correlation_id: Mapped[Optional[uuid.UUID]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User")
