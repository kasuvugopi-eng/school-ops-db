import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.enums import AssignmentState, SubmissionState, AssignmentTargetType
from app.services.audit_service import log_event
from app.services.user_service import get_students_for_class

ASSIGNMENT_TRANSITIONS = {
    AssignmentState.DRAFT: {AssignmentState.ACTIVE, AssignmentState.PENDING_APPROVAL},
    AssignmentState.PENDING_APPROVAL: {AssignmentState.ACTIVE, AssignmentState.DRAFT},
    AssignmentState.ACTIVE: {AssignmentState.COMPLETED, AssignmentState.CANCELLED}
}

def validate_assignment_transition(current: AssignmentState, target: AssignmentState) -> bool:
    if current == target:
        return True
    if target not in ASSIGNMENT_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition from {current} to {target}")
    return True

async def create_assignment(db: AsyncSession, data: dict, target_class_id: uuid.UUID, user: dict):
    data = {k: v for k, v in data.items() if k != "target_class_id"}
    assignment = Assignment(**data, created_by=user.id, school_id=user.school_id, target_class_id=target_class_id)
    db.add(assignment)
    await db.flush()
    
    await log_event(db, "assignment.created", school_id=user.school_id, actor_id=user.id, resource_type="assignment", resource_id=assignment.id)
    
    from app.services.submission_service import create_submissions_for_assignment
    await create_submissions_for_assignment(db, assignment.id, assignment.target_student_ids, [target_class_id])
    
    await db.commit()
    await db.refresh(assignment)
    
def format_datetime_ist(dt) -> str:
    if not dt:
        return "N/A"
    if isinstance(dt, datetime):
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(ist_tz)
        return ist_dt.strftime("%d-%m-%Y %I:%M %p IST")
    return str(dt)

async def notify_students_for_assignment(db: AsyncSession, assignment: Assignment):
    from app.models.user import User
    from app.models.grade_class import GradeClass
    from app.models.student_enrollment import StudentEnrollment
    from app.telegram.bot import send_telegram_message

    # Strict Quiet Hours Check: Night 10:00 PM (22) to Morning 7:00 AM (7) IST
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(ist_tz)
    now_hour = now_ist.hour

    # Fetch teacher name
    teacher_res = await db.execute(select(User.full_name).where(User.id == assignment.created_by))
    teacher_name = teacher_res.scalar_one_or_none() or "Teacher"

    # Fetch class and grade level info
    class_name = "All Classes"
    grade = "General"
    if assignment.target_class_id:
        cls_res = await db.execute(select(GradeClass).where(GradeClass.id == assignment.target_class_id))
        target_cls = cls_res.scalar_one_or_none()
        if target_cls:
            class_name = target_cls.name
            grade = target_cls.grade_level or "General"

    # Redesigned Student Notification Message
    student_msg = (
        "📌 *Assignment Notification*\n\n"
        f"*Assignment name:* {assignment.title}\n"
        f"*class-grade:* {class_name} ({grade})\n"
        f"*subject:* {assignment.subject or 'General'}\n"
        f"*assigned date:* {format_datetime_ist(assignment.created_at)}\n"
        f"*due date:* {format_datetime_ist(assignment.due_date)}\n"
        f"*teacher name:* {teacher_name}\n\n"
        f"📝 *Instructions:* {assignment.instructions or 'See portal for details.'}"
    )

    # Find notifiable enrolled students
    if assignment.target_class_id:
        students_query = select(User).join(StudentEnrollment, StudentEnrollment.student_id == User.id).where(
            StudentEnrollment.class_id == assignment.target_class_id,
            User.telegram_chat_id.isnot(None)
        )
    else:
        students_query = select(User).join(Submission, Submission.student_id == User.id).where(
            Submission.assignment_id == assignment.id, 
            User.telegram_chat_id.isnot(None)
        )
    students_res = await db.execute(students_query)
    notifiable_students = students_res.scalars().all()

    # Quiet Hours Policy (10 PM - 7 AM IST): Queue notifications for 7 AM
    if now_hour >= 22 or now_hour < 7:
        from app.models.reminder import Reminder
        from app.models.enums import ReminderType, ReminderState

        next_7am = now_ist.replace(hour=7, minute=0, second=0, microsecond=0)
        if now_hour >= 22:
            next_7am += timedelta(days=1)

        for student in notifiable_students:
            reminder = Reminder(
                assignment_id=assignment.id,
                target_student_id=student.id,
                reminder_type=ReminderType.UPCOMING,
                scheduled_for=next_7am,
                state=ReminderState.SCHEDULED,
                message_text=student_msg
            )
            db.add(reminder)
        await db.commit()
        await log_event(db, correlation_id=uuid.uuid4(), school_id=assignment.school_id, actor_type="system", event_type="assignment.notification_queued_quiet_hours", resource_type="assignment", resource_id=assignment.id, details={"quiet_hours": "10 PM - 7 AM IST", "scheduled_for": str(next_7am)})

        # Teacher Delivery Confirmation with Quiet Hours notice
        teacher_user_res = await db.execute(select(User).where(User.id == assignment.created_by))
        teacher_user = teacher_user_res.scalar_one_or_none()
        if teacher_user and teacher_user.telegram_chat_id:
            teacher_msg = (
                "✅ *Assignment Published Successfully!*\n\n"
                f"*assignment name:* {assignment.title}\n"
                f"*class-grade:* {class_name} ({grade})\n"
                f"*assigned date:* {format_datetime_ist(assignment.created_at)}\n"
                f"*due date:* {format_datetime_ist(assignment.due_date)}\n\n"
                f"🌙 _Quiet Hours Policy Active (10 PM - 7 AM IST). Student notifications scheduled for 7:00 AM._"
            )
            await send_telegram_message(teacher_user.telegram_chat_id, teacher_msg)
        return

    # Outside Quiet Hours (7 AM - 10 PM IST): Send immediate Telegram notifications
    for student in notifiable_students:
        await send_telegram_message(student.telegram_chat_id, student_msg)

        # Also notify linked Parents (Guardians)
        from app.models.guardian_link import GuardianLink
        g_res = await db.execute(
            select(User).join(GuardianLink, GuardianLink.guardian_id == User.id).where(
                GuardianLink.student_id == student.id,
                User.telegram_chat_id.isnot(None)
            )
        )
        guardians = g_res.scalars().all()
        for g in guardians:
            parent_asgn_msg = (
                "📢 *Child New Homework / Project Assignment*\n\n"
                f"A new assignment has been issued for your child *{student.full_name}*!\n\n"
                f"*Assignment:* {assignment.title}\n"
                f"*Class:* {class_name} ({grade})\n"
                f"*Subject:* {assignment.subject or 'General'}\n"
                f"*Due Date:* {format_datetime_ist(assignment.due_date)}\n"
                f"*Teacher:* {teacher_name}\n\n"
                f"📝 *Instructions:* {assignment.instructions or 'See portal for details.'}"
            )
            await send_telegram_message(g.telegram_chat_id, parent_asgn_msg)

    # Teacher Delivery Confirmation
    teacher_user_res = await db.execute(select(User).where(User.id == assignment.created_by))
    teacher_user = teacher_user_res.scalar_one_or_none()
    if teacher_user and teacher_user.telegram_chat_id:
        teacher_msg = (
            "✅ *Assignment Published Successfully!*\n\n"
            f"*assignment name:* {assignment.title}\n"
            f"*class-grade:* {class_name} ({grade})\n"
            f"*assigned date:* {format_datetime_ist(assignment.created_at)}\n"
            f"*due date:* {format_datetime_ist(assignment.due_date)}\n\n"
            f"💡 _Need to cancel? Reply `/cancel_assignment {assignment.id}` or `/cancel`_"
        )
        await send_telegram_message(teacher_user.telegram_chat_id, teacher_msg)

async def create_assignment(db: AsyncSession, data: dict, target_class_id: uuid.UUID, user: dict):
    data = {k: v for k, v in data.items() if k != "target_class_id"}
    assignment = Assignment(**data, created_by=user.id, school_id=user.school_id, target_class_id=target_class_id)
    db.add(assignment)
    await db.flush()
    
    await log_event(db, "assignment.created", school_id=user.school_id, actor_id=user.id, resource_type="assignment", resource_id=assignment.id)
    
    from app.services.submission_service import create_submissions_for_assignment
    await create_submissions_for_assignment(db, assignment.id, assignment.target_student_ids, [target_class_id])
    
    await db.commit()
    await db.refresh(assignment)
    
    if assignment.state == AssignmentState.ACTIVE:
        await notify_students_for_assignment(db, assignment)
            
    return assignment

async def list_assignments(db: AsyncSession, school_id: uuid.UUID, class_id: uuid.UUID = None, teacher_id: uuid.UUID = None, state: AssignmentState = None):
    query = select(Assignment).where(Assignment.school_id == school_id)
    if class_id:
        query = query.where(Assignment.target_class_id == class_id)
    if teacher_id: query = query.where(Assignment.created_by == teacher_id)
    if state: query = query.where(Assignment.state == state)
    result = await db.execute(query)
    return result.scalars().all()

async def get_assignment(db: AsyncSession, assignment_id: uuid.UUID):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if assignment:
        # Fetch submission summary
        sub_query = select(Submission.state, func.count(Submission.id)).where(Submission.assignment_id == assignment_id).group_by(Submission.state)
        sub_result = await db.execute(sub_query)
        assignment.submission_summary = {state.value: count for state, count in sub_result.all()}
    return assignment

async def notify_students_cancelled_assignment(db: AsyncSession, assignment: Assignment):
    from app.models.user import User
    from app.models.student_enrollment import StudentEnrollment
    if assignment.target_class_id:
        students_query = select(User).join(StudentEnrollment, StudentEnrollment.student_id == User.id).where(
            StudentEnrollment.class_id == assignment.target_class_id,
            User.telegram_chat_id.isnot(None)
        )
    else:
        students_query = select(User).join(Submission, Submission.student_id == User.id).where(
            Submission.assignment_id == assignment.id, 
            User.telegram_chat_id.isnot(None)
        )
    students_res = await db.execute(students_query)
    notifiable_students = students_res.scalars().all()
    
    from app.telegram.bot import send_telegram_message
    msg = f"❌ *Assignment Cancelled: {assignment.title}*\n\n"
    if assignment.subject:
        msg += f"📚 *Subject*: {assignment.subject}\n"
    msg += "\n⚠️ This assignment has been cancelled by your teacher."
    
    for student in notifiable_students:
        await send_telegram_message(student.telegram_chat_id, msg)

async def update_assignment_state(db: AsyncSession, assignment_id: uuid.UUID, new_state: AssignmentState, user: dict):
    assignment = await get_assignment(db, assignment_id)
    if not assignment:
        raise ValueError("Assignment not found")
    if assignment.state == new_state:
        return assignment
    validate_assignment_transition(assignment.state, new_state)
    assignment.state = new_state
    await db.commit()
    await db.refresh(assignment)
    
    if new_state == AssignmentState.ACTIVE:
        event_name = "assignment.activated"
        await notify_students_for_assignment(db, assignment)
    elif new_state == AssignmentState.CANCELLED:
        event_name = "assignment.cancelled"
        await notify_students_cancelled_assignment(db, assignment)
    else:
        event_name = "assignment.state_updated"
        
    await log_event(db, correlation_id=uuid.uuid4(), school_id=assignment.school_id, actor_id=user.id, actor_type="user", event_type=event_name, resource_type="assignment", resource_id=assignment.id, details={"new_state": new_state.value})
    return assignment

async def get_assignment_with_submissions(db: AsyncSession, assignment_id: uuid.UUID):
    assignment = await get_assignment(db, assignment_id)
    if not assignment:
        return None
    subs = await db.execute(select(Submission).where(Submission.assignment_id == assignment_id))
    return {"assignment": assignment, "submissions": subs.scalars().all()}
