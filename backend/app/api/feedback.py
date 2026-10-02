import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import require_role, get_current_user
from app.auth.permissions import assert_teacher_of_class, assert_same_school
from app.models.enums import UserRole, FeedbackAction, SubmissionState
from app.models.user import User
from app.models.submission import Submission
from app.models.assignment import Assignment
from app.models.feedback import Feedback as FeedbackModel
from app.services.submission_service import validate_submission_transition
from app.services.audit_service import log_event
from app.websocket.events import emit_feedback_given
from pydantic import BaseModel

router = APIRouter()

class CreateFeedbackBody(BaseModel):
    content: str
    action: str  # COMMENT, REVISION_REQUEST, APPROVAL

@router.post("/{submission_id}/feedback")
async def create_feedback(
    submission_id: uuid.UUID,
    body: CreateFeedbackBody,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Get assignment to verify teacher access
    assign_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = assign_result.scalar_one()
    assert_same_school(current_user, assignment.school_id)
    
    try:
        action = FeedbackAction(body.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}")
    
    # Create feedback
    fb = FeedbackModel(
        submission_id=submission_id, teacher_id=current_user.id,
        content=body.content, action=action
    )
    db.add(fb)
    
    # Auto-transition submission based on feedback action
    if action == FeedbackAction.REVISION_REQUEST:
        try:
            validate_submission_transition(sub.state, SubmissionState.REVISION_REQUESTED)
            sub.state = SubmissionState.REVISION_REQUESTED
        except ValueError:
            pass  # Can't transition, just add the feedback
    elif action == FeedbackAction.APPROVAL:
        try:
            validate_submission_transition(sub.state, SubmissionState.COMPLETED)
            sub.state = SubmissionState.COMPLETED
        except ValueError:
            pass
    
    await log_event(db, "feedback.created", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="feedback",
                    resource_id=fb.id, details={"action": body.action, "submission_id": str(submission_id)})
    await db.commit()
    
    await emit_feedback_given(str(assignment.school_id), {
        "submission_id": str(submission_id), "teacher_name": current_user.full_name,
        "action": body.action, "assignment_title": assignment.title
    })
    
    return {"id": str(fb.id), "action": fb.action.value, "content": fb.content}

@router.get("/{submission_id}/feedback")
async def list_feedback(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FeedbackModel, User.full_name)
        .join(User, FeedbackModel.teacher_id == User.id)
        .where(FeedbackModel.submission_id == submission_id)
        .order_by(FeedbackModel.created_at.asc())
    )
    return [{
        "id": str(fb.id), "teacher_id": str(fb.teacher_id), "teacher_name": name,
        "content": fb.content, "action": fb.action.value, "created_at": str(fb.created_at)
    } for fb, name in result.all()]
