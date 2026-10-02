from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import FeedbackAction

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id"), nullable=False)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[FeedbackAction] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    submission = relationship("Submission", back_populates="feedback_items")
    teacher = relationship("User")
