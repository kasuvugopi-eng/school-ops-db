from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid
from app.models.enums import UserRole

class CreateInviteRequest(BaseModel):
    role: UserRole
    target_class_id: Optional[uuid.UUID] = None
    target_student_id: Optional[uuid.UUID] = None
    relationship: Optional[str] = None
    expires_hours: int = 48

class InviteResponse(BaseModel):
    id: uuid.UUID
    token: str
    role: UserRole
    target_class_id: Optional[uuid.UUID]
    expires_at: datetime
    created_at: datetime
    invite_url: Optional[str] = None
    
    model_config = {"from_attributes": True}

class AcceptInviteRequest(BaseModel):
    token: str
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
