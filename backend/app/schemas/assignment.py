from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from app.models.enums import AssignmentTargetType, AssignmentState

class CreateAssignmentRequest(BaseModel):
    title: str
    subject: Optional[str] = None
    instructions: Optional[str] = None
    due_date: Optional[datetime] = None
    target_type: AssignmentTargetType
    target_class_id: uuid.UUID
    student_ids: Optional[List[uuid.UUID]] = None

class AssignmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject: Optional[str]
    instructions: Optional[str]
    due_date: Optional[datetime]
    target_type: AssignmentTargetType
    state: AssignmentState
    created_by: uuid.UUID
    created_at: datetime
    target_class_id: Optional[uuid.UUID] = None
    submission_summary: Dict[str, int] = {}
    
    model_config = {"from_attributes": True}

class UpdateAssignmentStateRequest(BaseModel):
    new_state: AssignmentState
