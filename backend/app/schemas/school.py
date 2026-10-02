from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class SchoolResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    address: Optional[str]
    timezone: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UpdateSchoolRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
