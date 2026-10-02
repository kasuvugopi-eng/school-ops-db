from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid
from app.models.enums import UserRole

class RegisterSchoolRequest(BaseModel):
    school_name: str
    school_code: str
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str
    admin_phone: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    school_id: Optional[uuid.UUID]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
