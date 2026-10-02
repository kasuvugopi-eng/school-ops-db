from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import uuid
from app.models.enums import DocumentType, ParseApprovalState

class DocumentResponse(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    mime_type: Optional[str]
    file_size: Optional[int]
    uploaded_by: uuid.UUID
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ParseResultResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    parsed_data: dict
    ambiguity_flags: list
    confidence_notes: dict
    approval_state: ParseApprovalState
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ApproveParseRequest(BaseModel):
    approved: bool
    edits: Optional[dict] = None
