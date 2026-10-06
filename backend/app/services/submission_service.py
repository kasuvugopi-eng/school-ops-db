import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.submission import Submission
from app.models.enums import SubmissionState

SUBMISSION_TRANSITIONS = {
    SubmissionState.NOT_STARTED: {SubmissionState.IN_PROGRESS, SubmissionState.BLOCKED, SubmissionState.SUBMITTED},
    SubmissionState.IN_PROGRESS: {SubmissionState.BLOCKED, SubmissionState.SUBMITTED},
    SubmissionState.BLOCKED: {SubmissionState.IN_PROGRESS, SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED},
    SubmissionState.SUBMITTED: {SubmissionState.REVISION_REQUESTED, SubmissionState.COMPLETED},
    SubmissionState.REVISION_REQUESTED: {SubmissionState.BLOCKED, SubmissionState.RESUBMITTED},
    SubmissionState.RESUBMITTED: {SubmissionState.COMPLETED, SubmissionState.REVISION_REQUESTED}
}

def validate_submission_transition(current: SubmissionState, target: SubmissionState) -> bool:
    if current == target:
        return True
    if target not in SUBMISSION_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition from {current} to {target}")
    return True

async def update_submission_state(db: AsyncSession, submission_id: uuid.UUID, new_state: SubmissionState, content_text: str = None, blocked_reason: str = None, attachment_id: uuid.UUID = None):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise ValueError("Submission not found")
    
    validate_submission_transition(submission.state, new_state)
    submission.state = new_state
    if content_text is not None:
        submission.content_text = content_text
    if blocked_reason is not None:
        submission.blocked_reason = blocked_reason
    if attachment_id is not None:
        submission.attachment_document_id = attachment_id
        
    if new_state in (SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
        submission.submitted_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(submission)
    
    if new_state in (SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
        await notify_submission_created_or_updated(db, submission)
        
    return submission

async def notify_submission_created_or_updated(db: AsyncSession, submission: Submission):
    from app.models.assignment import Assignment
    from app.models.user import User
    from app.models.grade_class import GradeClass
    from app.telegram.bot import send_telegram_message
    from app.services.assignment_service import format_datetime_ist

    # Fetch assignment
    asgn_res = await db.execute(select(Assignment).where(Assignment.id == submission.assignment_id))
    assignment = asgn_res.scalar_one_or_none()
    if not assignment:
        return

    # Fetch student
    student_res = await db.execute(select(User).where(User.id == submission.student_id))
    student = student_res.scalar_one_or_none()
    if not student:
        return

    # Fetch class and grade level info
    class_name = "All Classes"
    grade = "General"
    if assignment.target_class_id:
        cls_res = await db.execute(select(GradeClass).where(GradeClass.id == assignment.target_class_id))
        target_cls = cls_res.scalar_one_or_none()
        if target_cls:
            class_name = target_cls.name
            grade = target_cls.grade_level or "General"

    submitted_date_str = format_datetime_ist(submission.submitted_at or datetime.now(timezone.utc))

    # 1. Delivery Confirmation to Student
    if student.telegram_chat_id:
        student_delivery_msg = (
            "✅ *Assignment Submitted Successfully!*\n\n"
            f"*Assignment name:* {assignment.title}\n"
            f"*class-grade:* {class_name} ({grade})\n"
            f"*subject:* {assignment.subject or 'General'}\n"
            f"*submitted date:* {submitted_date_str}\n"
            f"*status:* Submitted (Pending Teacher Review)"
        )
        await send_telegram_message(student.telegram_chat_id, student_delivery_msg)

    # 2. Notification Alert to Teacher (Web-only approval instruction)
    teacher_res = await db.execute(select(User).where(User.id == assignment.created_by))
    teacher = teacher_res.scalar_one_or_none()
    if teacher and teacher.telegram_chat_id:
        parsed_preview = submission.content_text or "Submitted via Telegram attachment"
        if len(parsed_preview) > 300:
            parsed_preview = parsed_preview[:300] + "..."

        teacher_alert_msg = (
            "📩 *New Assignment Submission Received!*\n\n"
            f"*Assignment name:* {assignment.title}\n"
            f"*class-grade:* {class_name} ({grade})\n"
            f"*student name:* {student.full_name}\n"
            f"*submitted date:* {submitted_date_str}\n\n"
            f"📄 *Extracted / Submitted Content Preview:*\n"
            f"_{parsed_preview}_\n\n"
            f"🌐 *Action Required:* Please log in to your Teacher Web Portal to review and approve this submission."
        )
        from app.telegram.routing import ref_tag
        teacher_alert_msg += ref_tag(student.id)
        await send_telegram_message(teacher.telegram_chat_id, teacher_alert_msg)

    # 3. Notification to Parent/Guardian
    from app.models.guardian_link import GuardianLink
    guardians_res = await db.execute(
        select(User).join(GuardianLink, GuardianLink.guardian_id == User.id).where(
            GuardianLink.student_id == student.id,
            User.telegram_chat_id.isnot(None)
        )
    )
    guardians = guardians_res.scalars().all()
    for guardian in guardians:
        parent_msg = (
            "👨‍👩‍👦 *Child Homework Submission Notice*\n\n"
            f"Your child *{student.full_name}* has submitted their homework!\n\n"
            f"*Assignment:* {assignment.title}\n"
            f"*Subject:* {assignment.subject or 'General'}\n"
            f"*Submitted Date:* {submitted_date_str}\n"
            f"*Status:* Submitted (Awaiting Teacher Review)"
        )
        await send_telegram_message(guardian.telegram_chat_id, parent_msg)

async def get_submission(db: AsyncSession, submission_id: uuid.UUID):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    return result.scalar_one_or_none()

async def list_submissions_for_student(db: AsyncSession, student_id: uuid.UUID):
    result = await db.execute(select(Submission).where(Submission.student_id == student_id))
    return result.scalars().all()

async def get_submissions_for_assignment(db: AsyncSession, assignment_id: uuid.UUID):
    # Would join with User for student names
    result = await db.execute(select(Submission).where(Submission.assignment_id == assignment_id))
    return result.scalars().all()

async def create_submissions_for_assignment(db: AsyncSession, assignment_id: uuid.UUID, target_student_ids: list, class_ids: list):
    # Get existing submission student IDs for idempotency
    existing_subs_result = await db.execute(select(Submission.student_id).where(Submission.assignment_id == assignment_id))
    existing_student_ids = {s_id for s_id in existing_subs_result.scalars()}
    
    if target_student_ids:
        # Specific students
        for sid_str in target_student_ids:
            sid = uuid.UUID(sid_str) if isinstance(sid_str, str) else sid_str
            if sid not in existing_student_ids:
                db.add(Submission(assignment_id=assignment_id, student_id=sid, state=SubmissionState.NOT_STARTED))
                existing_student_ids.add(sid)
    else:
        # All students in class_ids
        from app.models.student_enrollment import StudentEnrollment
        from app.models.user import User
        from app.models.enums import UserRole
        
        result = await db.execute(
            select(StudentEnrollment.student_id)
            .join(User, User.id == StudentEnrollment.student_id)
            .where(
                StudentEnrollment.class_id.in_(class_ids),
                User.is_active == True,
                User.role == UserRole.STUDENT
            )
        )
        students = result.scalars().all()
        for sid in students:
            if sid not in existing_student_ids:
                db.add(Submission(assignment_id=assignment_id, student_id=sid, state=SubmissionState.NOT_STARTED))
                existing_student_ids.add(sid)
