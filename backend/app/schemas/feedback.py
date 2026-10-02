from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from app.models.enums import FeedbackAction

class CreateFeedbackRequest(BaseModel):
    content: str
    action: FeedbackAction

class FeedbackResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    content: str
    action: FeedbackAction
    created_at: datetime
    
    model_config = {"from_attributes": True}
