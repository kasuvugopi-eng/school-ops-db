from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
from app.models.enums import SubmissionState
from app.schemas.feedback import FeedbackResponse

class UpdateSubmissionRequest(BaseModel):
    state: Optional[SubmissionState] = None
    content_text: Optional[str] = None
    blocked_reason: Optional[str] = None

class SubmissionResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    state: SubmissionState
    content_text: Optional[str]
    blocked_reason: Optional[str]
    submitted_at: Optional[datetime]
    created_at: datetime
    feedback: List[FeedbackResponse] = []
    
    model_config = {"from_attributes": True}
