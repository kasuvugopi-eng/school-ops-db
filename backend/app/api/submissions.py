import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school
from app.models.enums import UserRole, SubmissionState
from app.models.user import User
from app.models.submission import Submission
from app.models.assignment import Assignment
from app.models.feedback import Feedback
from app.services.submission_service import SUBMISSION_TRANSITIONS, validate_submission_transition
from app.services.audit_service import log_event
from app.websocket.events import emit_submission_update, emit_student_blocked
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class UpdateSubmissionBody(BaseModel):
    state: Optional[str] = None
    content_text: Optional[str] = None
    blocked_reason: Optional[str] = None

class SubmitWorkBody(BaseModel):
    content_text: str

@router.get("/mine")
async def list_my_submissions(
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Submission, Assignment.title, Assignment.subject, Assignment.due_date, Assignment.instructions)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(Submission.student_id == current_user.id)
        .order_by(Assignment.due_date.asc().nulls_last())
    )
    submissions = []
    for sub, title, subject, due_date, instructions in result.all():
        submissions.append({
            "id": str(sub.id), "assignment_id": str(sub.assignment_id),
            "student_id": str(sub.student_id), "state": sub.state.value,
            "content_text": sub.content_text, "blocked_reason": sub.blocked_reason,
            "submitted_at": str(sub.submitted_at) if sub.submitted_at else None,
            "created_at": str(sub.created_at),
            "assignment_title": title, "assignment_subject": subject,
            "assignment_due_date": str(due_date) if due_date else None,
            "assignment_instructions": instructions
        })
    return submissions

@router.get("/{id}")
async def get_submission(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Students can only see their own
    if current_user.role == UserRole.STUDENT and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get feedback
    fb_result = await db.execute(
        select(Feedback, User.full_name)
        .join(User, Feedback.teacher_id == User.id)
        .where(Feedback.submission_id == id)
        .order_by(Feedback.created_at.asc())
    )
    feedback = [{
        "id": str(fb.id), "teacher_id": str(fb.teacher_id), "teacher_name": name,
        "content": fb.content, "action": fb.action.value, "created_at": str(fb.created_at)
    } for fb, name in fb_result.all()]
    
    return {
        "id": str(sub.id), "assignment_id": str(sub.assignment_id),
        "student_id": str(sub.student_id), "state": sub.state.value,
        "content_text": sub.content_text, "blocked_reason": sub.blocked_reason,
        "submitted_at": str(sub.submitted_at) if sub.submitted_at else None,
        "created_at": str(sub.created_at), "feedback": feedback
    }

@router.put("/{id}")
async def update_submission(
    id: uuid.UUID,
    body: UpdateSubmissionBody,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    
    if body.state:
        try:
            new_state = SubmissionState(body.state)
            validate_submission_transition(sub.state, new_state)
            
            if new_state not in (SubmissionState.IN_PROGRESS, SubmissionState.BLOCKED):
                raise HTTPException(status_code=403, detail="Role violation")
                
            sub.state = new_state
            if new_state in (SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
                sub.submitted_at = datetime.now(timezone.utc)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    if body.content_text is not None:
        sub.content_text = body.content_text
    if body.blocked_reason is not None:
        sub.blocked_reason = body.blocked_reason
    
    # Get assignment for school_id
    assign_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = assign_result.scalar_one()
    
    await log_event(db, "submission.updated", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="submission",
                    resource_id=sub.id, details={"new_state": sub.state.value})
    await db.commit()
    
    # WebSocket notification
    if sub.state == SubmissionState.BLOCKED:
        await emit_student_blocked(str(assignment.school_id), {
            "submission_id": str(sub.id), "student_name": current_user.full_name,
            "assignment_title": assignment.title, "reason": sub.blocked_reason
        })
    else:
        await emit_submission_update(str(assignment.school_id), {
            "submission_id": str(sub.id), "student_name": current_user.full_name,
            "assignment_title": assignment.title, "state": sub.state.value
        })
    
    return {"id": str(sub.id), "state": sub.state.value}

@router.post("/{id}/submit")
async def submit_work(
    id: uuid.UUID,
    body: SubmitWorkBody,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    
    # Determine target state
    target = SubmissionState.RESUBMITTED if sub.state == SubmissionState.REVISION_REQUESTED else SubmissionState.SUBMITTED
    try:
        validate_submission_transition(sub.state, target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    sub.state = target
    sub.content_text = body.content_text
    sub.submitted_at = datetime.now(timezone.utc)
    
    assign_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = assign_result.scalar_one()
    
    await log_event(db, "submission.submitted", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="submission",
                    resource_id=sub.id)
    await db.commit()
    
    await emit_submission_update(str(assignment.school_id), {
        "submission_id": str(sub.id), "student_name": current_user.full_name,
        "assignment_title": assignment.title, "state": sub.state.value
    })
    
    return {"id": str(sub.id), "state": sub.state.value, "submitted_at": str(sub.submitted_at)}
