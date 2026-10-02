from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
import uuid

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    correlation_id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID]
    resource_type: Optional[str]
    resource_id: Optional[uuid.UUID]
    details: dict
    created_at: datetime
    
    model_config = {"from_attributes": True}

class AuditFilterParams(BaseModel):
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
