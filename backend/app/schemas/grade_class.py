from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class CreateClassRequest(BaseModel):
    name: str
    grade_level: Optional[str] = None

class UserBrief(BaseModel):
    id: str
    full_name: str
    email: str

class ClassResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    grade_level: Optional[str]
    created_at: datetime
    teacher_count: int = 0
    student_count: int = 0
    teachers: List[UserBrief] = []
    students: List[UserBrief] = []
    
    model_config = {"from_attributes": True}
