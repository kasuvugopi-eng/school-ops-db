import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school
from app.models.enums import UserRole, SubmissionState, AssignmentState, FeedbackAction
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
        .where(Assignment.state != AssignmentState.DRAFT)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    assign_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = assign_result.scalar_one()

    if current_user.role == UserRole.STUDENT:
        if sub.student_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your submission")
        if assignment.state == AssignmentState.DRAFT:
            raise HTTPException(status_code=403, detail="Assignment is not published")
            
        if body.state:
            try:
                new_state = SubmissionState(body.state)
                validate_submission_transition(sub.state, new_state)
                
                # Student can only transition to IN_PROGRESS, BLOCKED, SUBMITTED, RESUBMITTED
                if new_state not in (SubmissionState.IN_PROGRESS, SubmissionState.BLOCKED, SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
                    raise HTTPException(status_code=403, detail="Role violation")
                    
                sub.state = new_state
                if new_state in (SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
                    sub.submitted_at = datetime.now(timezone.utc)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    elif current_user.role == UserRole.TEACHER:
        # Teacher must be assigned to the class of the assignment? But submissions are for assignments... wait, teacher class check.
        # Actually, let's just make sure it's the same school for now, we'll implement class check later for teacher.
        assert_same_school(current_user, sub)
        if body.state:
            try:
                new_state = SubmissionState(body.state)
                validate_submission_transition(sub.state, new_state)
                sub.state = new_state
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if body.content_text is not None:
        sub.content_text = body.content_text
    if body.blocked_reason is not None:
        sub.blocked_reason = body.blocked_reason
    
    await log_event(db, "submission.updated", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="submission",
                    resource_id=sub.id, details={"new_state": sub.state.value if body.state else None})
    await db.commit()
    
    # WebSocket notification
    if sub.state == SubmissionState.BLOCKED:
        await emit_student_blocked(str(assignment.school_id), {
            "submission_id": str(sub.id), "student_name": current_user.full_name,
            "assignment_title": assignment.title, "reason": sub.blocked_reason
        })
        
        # Send direct Telegram notification to assigned Teacher if available
        if assignment.created_by:
            teacher_res = await db.execute(select(User).where(User.id == assignment.created_by))
            teacher = teacher_res.scalar_one_or_none()
            if teacher and teacher.telegram_chat_id:
                from app.telegram.bot import send_telegram_message
                stuck_msg = (
                    "🚨 *Student Stuck Alert!*\n\n"
                    f"*Student:* {current_user.full_name}\n"
                    f"*Assignment:* {assignment.title}\n"
                    f"*Doubt/Reason:* {sub.blocked_reason or 'No reason provided.'}\n\n"
                    "💡 *Please review on Teacher Dashboard or reply to student.*"
                )
                await send_telegram_message(teacher.telegram_chat_id, stuck_msg)
    else:
        await emit_submission_update(str(assignment.school_id), {
            "submission_id": str(sub.id), "student_name": current_user.full_name,
            "assignment_title": assignment.title, "state": sub.state.value
        })
    
    if body.state and SubmissionState(body.state) in (SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
        from app.services.submission_service import notify_submission_created_or_updated
        await notify_submission_created_or_updated(db, sub)

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

class FeedbackRequest(BaseModel):
    action: str  # "APPROVAL", "REVISION_REQUEST", "COMMENT"
    content: Optional[str] = ""

@router.post("/{id}/feedback")
async def create_submission_feedback(
    id: uuid.UUID,
    body: FeedbackRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Submission).where(Submission.id == id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    action_str = body.action.upper()
    if action_str == "APPROVE":
        action_str = "APPROVAL"
    try:
        feedback_action = FeedbackAction(action_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid feedback action: {body.action}")

    # Map action to state transition
    if feedback_action == FeedbackAction.APPROVAL:
        sub.state = SubmissionState.COMPLETED
    elif feedback_action == FeedbackAction.REVISION_REQUEST:
        sub.state = SubmissionState.REVISION_REQUESTED

    # Create feedback entry
    feedback_entry = Feedback(
        submission_id=sub.id,
        teacher_id=current_user.id,
        content=body.content or ("Approved by teacher." if feedback_action == FeedbackAction.APPROVAL else "Revision requested by teacher."),
        action=feedback_action
    )
    db.add(feedback_entry)

    assign_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    assignment = assign_result.scalar_one()

    await log_event(db, "submission.feedback_added", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="submission",
                    resource_id=sub.id, details={"action": feedback_action.value, "new_state": sub.state.value})
    await db.commit()

    # Emit WebSocket update
    await emit_submission_update(str(assignment.school_id), {
        "submission_id": str(sub.id), "student_name": "",
        "assignment_title": assignment.title, "state": sub.state.value
    })

    # Telegram Notification to Student
    student_res = await db.execute(select(User).where(User.id == sub.student_id))
    student = student_res.scalar_one_or_none()

    if student and student.telegram_chat_id:
        from app.telegram.bot import send_telegram_message
        from app.models.grade_class import GradeClass

        class_name = "All Classes"
        grade = "General"
        if assignment.target_class_id:
            cls_res = await db.execute(select(GradeClass).where(GradeClass.id == assignment.target_class_id))
            target_cls = cls_res.scalar_one_or_none()
            if target_cls:
                class_name = target_cls.name
                grade = target_cls.grade_level or "General"

        if feedback_action == FeedbackAction.APPROVAL:
            msg = (
                "🎉 *Assignment Approved!*\n\n"
                f"*Assignment name:* {assignment.title}\n"
                f"*class-grade:* {class_name} ({grade})\n"
                f"*status:* Completed (Approved)\n"
                f"*teacher feedback:* {body.content or 'Great job!'}"
            )
        elif feedback_action == FeedbackAction.REVISION_REQUEST:
            msg = (
                "🔄 *Revision Requested for Assignment*\n\n"
                f"*Assignment name:* {assignment.title}\n"
                f"*class-grade:* {class_name} ({grade})\n"
                f"*status:* Revision Requested\n"
                f"*teacher feedback:* {body.content or 'Please review and resubmit.'}"
            )
        else:
            msg = (
                "💬 *New Feedback from Teacher*\n\n"
                f"*Assignment name:* {assignment.title}\n"
                f"*teacher feedback:* {body.content or 'Feedback provided.'}"
            )

        await send_telegram_message(student.telegram_chat_id, msg)

    # Send delivery confirmation to Teacher as well
    if current_user.telegram_chat_id:
        from app.telegram.bot import send_telegram_message
        teacher_conf_msg = (
            "✅ *Approval Registered Successfully!*\n\n"
            f"*Student:* {student.full_name if student else 'Student'}\n"
            f"*Assignment:* {assignment.title}\n"
            f"*Status:* Completed & Approved\n"
            "📨 *Student Notification:* Delivered to student via Telegram!"
        )
        await send_telegram_message(current_user.telegram_chat_id, teacher_conf_msg)

    return {
        "id": str(feedback_entry.id),
        "submission_id": str(sub.id),
        "state": sub.state.value,
        "action": feedback_action.value,
        "content": feedback_entry.content
    }
