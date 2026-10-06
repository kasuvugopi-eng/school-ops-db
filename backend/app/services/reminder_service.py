from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.reminder import Reminder
from app.models.school_policy import SchoolPolicy
from app.models.enums import AssignmentState, SubmissionState, ReminderState, ReminderType, PolicyType
from app.services.audit_service import log_event
import uuid

async def get_quiet_hours(db: AsyncSession, school_id: uuid.UUID) -> tuple[int, int, bool]:
    """Get quiet hours for a school. Returns (start_hour, end_hour, is_active)."""
    result = await db.execute(
        select(SchoolPolicy).where(
            SchoolPolicy.school_id == school_id,
            SchoolPolicy.policy_type == PolicyType.QUIET_HOURS
        )
    )
    policy = result.scalar_one_or_none()
    if policy and policy.config:
        return (
            policy.config.get('start', 21),
            policy.config.get('end', 7),
            policy.is_active
        )
    return (21, 7, True)  # Default quiet hours

def is_quiet_hours(start: int, end: int, is_active: bool = True) -> bool:
    if not is_active:
        return False
    from datetime import datetime, timezone, timedelta
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    now_hour = ist_now.hour

    if start > end:  # e.g., 21 to 7 (crosses midnight)
        return now_hour >= start or now_hour < end
    elif start < end:
        return start <= now_hour < end
    else:
        return False

async def process_reminders_for_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> dict:
    """Process reminders for a single assignment. Returns summary."""
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment or assignment.state != AssignmentState.ACTIVE or not assignment.due_date:
        return {"skipped": "assignment not active or no due date"}
    
    quiet_start, quiet_end, is_active = await get_quiet_hours(db, assignment.school_id)
    in_quiet = is_quiet_hours(quiet_start, quiet_end, is_active)
    
    # Get all submissions for this assignment
    subs_result = await db.execute(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    submissions = subs_result.scalars().all()
    
    summary = {"sent": 0, "queued": 0, "skipped_submitted": 0, "escalated": 0}
    
    from datetime import datetime, timezone, timedelta
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    
    # Assignment due date in UTC & IST
    due_utc = assignment.due_date if assignment.due_date.tzinfo else assignment.due_date.replace(tzinfo=timezone.utc)
    due_ist = due_utc + timedelta(hours=5, minutes=30)
    
    from app.telegram.bot import send_telegram_message
    from app.models.user import User
    
    for sub in submissions:
        # STRICT RULE: Skip students who already submitted
        if sub.state in (SubmissionState.COMPLETED, SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
            summary["skipped_submitted"] += 1
            continue
        
        if sub.state == SubmissionState.BLOCKED:
            existing_esc = await db.execute(
                select(Reminder).where(
                    Reminder.assignment_id == assignment_id,
                    Reminder.target_student_id == sub.student_id,
                    Reminder.reminder_type == ReminderType.ESCALATION,
                    Reminder.escalation_level == 1
                )
            )
            if existing_esc.scalar_one_or_none():
                continue

            reminder = Reminder(
                assignment_id=assignment_id,
                target_student_id=sub.student_id,
                reminder_type=ReminderType.ESCALATION,
                scheduled_for=utc_now,
                sent_at=utc_now,
                state=ReminderState.SENT,
                escalation_level=1,
                message_text=f"🚨 Student is blocked on assignment: '{assignment.title}'. Reason: {sub.blocked_reason or 'Not specified'}"
            )
            db.add(reminder)
            summary["escalated"] += 1
            await log_event(db, event_type="reminder.escalated", school_id=assignment.school_id,
                          resource_type="submission", resource_id=sub.id,
                          details={"student_id": str(sub.student_id), "blocked_reason": sub.blocked_reason})
            continue

        # Get Student Telegram Chat ID
        user_res = await db.execute(select(User).where(User.id == sub.student_id))
        user = user_res.scalar_one_or_none()

        # Check Triggers for Upcoming & Overdue Reminders
        # 1. 24 Hours Before Alert (escalation_level = 10)
        time_until_due = due_utc - utc_now
        
        triggers = []
        
        # Trigger 1: 24 Hours Before (within 24h window)
        if timedelta(hours=0) < time_until_due <= timedelta(hours=24):
            triggers.append((10, ReminderType.UPCOMING, f"⏰ **24-HOUR REMINDER**: Assignment '{assignment.title}' is due in 24 hours! (Due: {due_ist.strftime('%d %b %Y, %I:%M %p IST')})"))

        # Trigger 2: Due Date Morning 07:05 AM IST Alert (escalation_level = 20)
        if ist_now.date() == due_ist.date() and ist_now.hour >= 7:
            triggers.append((20, ReminderType.UPCOMING, f"🌅 **MORNING REMINDER**: Reminder to complete assignment '{assignment.title}' today by {due_ist.strftime('%I:%M %p IST')}!"))

        # Trigger 3: 30 Minutes Before Urgent Alert (escalation_level = 30)
        if timedelta(minutes=0) < time_until_due <= timedelta(minutes=30):
            triggers.append((30, ReminderType.UPCOMING, f"⚠️ **URGENT (30 MINS LEFT)**: Assignment '{assignment.title}' is due in 30 minutes! Please submit now."))

        # Trigger 4: Overdue Alert (escalation_level = 40)
        if utc_now > due_utc:
            triggers.append((40, ReminderType.OVERDUE, f"🚨 **OVERDUE ALERT**: Assignment '{assignment.title}' was due at {due_ist.strftime('%I:%M %p IST')} and is now OVERDUE! Please submit as soon as possible."))

        for level, r_type, msg in triggers:
            # Idempotency check: level + type + assignment + student
            existing_rem = await db.execute(
                select(Reminder).where(
                    Reminder.assignment_id == assignment_id,
                    Reminder.target_student_id == sub.student_id,
                    Reminder.reminder_type == r_type,
                    Reminder.escalation_level == level
                )
            )
            if existing_rem.scalar_one_or_none():
                continue

            if in_quiet:
                # Queue for sending after quiet hours
                reminder = Reminder(
                    assignment_id=assignment_id,
                    target_student_id=sub.student_id,
                    reminder_type=r_type,
                    scheduled_for=utc_now,
                    state=ReminderState.SCHEDULED,
                    escalation_level=level,
                    message_text=msg
                )
                db.add(reminder)
                summary["queued"] += 1
            else:
                # Send immediately
                if user and user.telegram_chat_id:
                    await send_telegram_message(user.telegram_chat_id, msg)
                reminder = Reminder(
                    assignment_id=assignment_id,
                    target_student_id=sub.student_id,
                    reminder_type=r_type,
                    scheduled_for=utc_now,
                    sent_at=utc_now,
                    state=ReminderState.SENT,
                    escalation_level=level,
                    message_text=msg
                )
                db.add(reminder)
                summary["sent"] += 1

            await log_event(db, event_type="reminder.sent", school_id=assignment.school_id,
                          resource_type="submission", resource_id=sub.id,
                          details={"student_id": str(sub.student_id), "level": level, "is_overdue": r_type == ReminderType.OVERDUE})

    return summary

async def process_queued_reminders(db: AsyncSession) -> int:
    # Fetch first active school's policy or default
    res = await db.execute(select(SchoolPolicy).where(SchoolPolicy.policy_type == PolicyType.QUIET_HOURS))
    pol = res.scalars().first()
    if pol and pol.config:
        if is_quiet_hours(pol.config.get('start', 21), pol.config.get('end', 7), pol.is_active):
            return 0
    
    result = await db.execute(
        select(Reminder).where(
            Reminder.state == ReminderState.SCHEDULED,
            Reminder.scheduled_for <= datetime.now(timezone.utc)
        )
    )
    scheduled_reminders = result.scalars().all()
    from app.telegram.bot import send_telegram_message
    from app.models.user import User
    
    count = 0
    for rem in scheduled_reminders:
        user_res = await db.execute(select(User).where(User.id == rem.target_student_id))
        user = user_res.scalar_one_or_none()
        if user and user.telegram_chat_id:
            await send_telegram_message(user.telegram_chat_id, rem.message_text or "Notification")
        rem.state = ReminderState.SENT
        rem.sent_at = datetime.now(timezone.utc)
        count += 1
    await db.commit()
    return count

async def process_all_active_reminders(db: AsyncSession) -> dict:
    """Process reminders for all active assignments and flush queued quiet hours notifications."""
    queued_sent = await process_queued_reminders(db)
    result = await db.execute(
        select(Assignment).where(Assignment.state == AssignmentState.ACTIVE)
    )
    assignments = result.scalars().all()
    
    results = {"queued_sent": queued_sent}
    for assignment in assignments:
        results[str(assignment.id)] = await process_reminders_for_assignment(db, assignment.id)
    
    return results
