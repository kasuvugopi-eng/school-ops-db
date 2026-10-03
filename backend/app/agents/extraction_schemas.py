from pydantic import BaseModel, Field
from typing import Optional

class ParsedAssignment(BaseModel):
    title: Optional[str] = Field(None, description="Assignment title")
    subject: Optional[str] = Field(None, description="Subject area")
    instructions: Optional[str] = Field(None, description="Full assignment instructions")
    due_date: Optional[str] = Field(None, description="Due date in ISO 8601 format YYYY-MM-DD")
    target_class_id: Optional[str] = Field(None, description="Target class/grade name")
    target_students: Optional[list[str]] = Field(None, description="Specific student names if individual/group")
    attachments_mentioned: Optional[list[str]] = Field(None, description="Referenced attachment filenames")
    constraints: Optional[list[str]] = Field(None, description="Special constraints or rules")
    ambiguities: list[str] = Field(default_factory=list, description="Fields that are unclear or missing")
    confidence: float = Field(0.0, ge=0, le=1, description="Overall parse confidence 0-1")

class ParsedRosterRow(BaseModel):
    student_name: str
    grade_class: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    notes: Optional[str] = None
    flags: list[str] = Field(default_factory=list, description="Duplicate, missing data, ambiguous")

class DuplicateCandidate(BaseModel):
    row: int = Field(description="Row index of the duplicate")
    name: str = Field(description="Name of the student that is duplicated")

class ParsedRoster(BaseModel):
    rows: list[ParsedRosterRow]
    ambiguities: list[str] = Field(default_factory=list)
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list, description="Pairs of rows that might be duplicates")

class DetectedIntent(BaseModel):
    intent: str = Field(description="One of the defined intent categories")
    confidence: float = Field(ge=0, le=1)
    extracted_entities: dict = Field(default_factory=dict)
    reasoning: str = Field(description="Why this intent was chosen")
    is_safe: bool = Field(True, description="Whether the message is safe to process")

class ParsedPolicy(BaseModel):
    quiet_hours_start: Optional[int] = Field(None, description="Hour when quiet hours begin (0-23)")
    quiet_hours_end: Optional[int] = Field(None, description="Hour when quiet hours end (0-23)")
    escalation_after_missed: Optional[int] = Field(None, description="Number of missed reminders before escalation")
    teacher_approval_required: Optional[bool] = Field(None, description="Whether teacher approval is required for AI actions")
    allowed_channels: Optional[list[str]] = Field(None, description="Allowed communication channels")
    ambiguities: list[str] = Field(default_factory=list)
