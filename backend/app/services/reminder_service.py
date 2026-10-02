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

async def get_quiet_hours(db: AsyncSession, school_id: uuid.UUID) -> tuple[int, int]:
    """Get quiet hours for a school. Returns (start_hour, end_hour)."""
    result = await db.execute(
        select(SchoolPolicy).where(
            SchoolPolicy.school_id == school_id,
            SchoolPolicy.policy_type == PolicyType.QUIET_HOURS,
            SchoolPolicy.is_active == True
        )
    )
    policy = result.scalar_one_or_none()
    if policy and policy.config:
        return (
            policy.config.get('start', 21),
            policy.config.get('end', 7)
        )
    return (21, 7)  # Default quiet hours

def is_quiet_hours(start: int, end: int) -> bool:
    now_hour = datetime.now(timezone.utc).hour
    if start > end:  # e.g., 21 to 7 (crosses midnight)
        return now_hour >= start or now_hour < end
    else:
        return start <= now_hour < end

async def process_reminders_for_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> dict:
    """Process reminders for a single assignment. Returns summary."""
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment or assignment.state != AssignmentState.ACTIVE:
        return {"skipped": "assignment not active"}
    
    # Check quiet hours
    quiet_start, quiet_end = await get_quiet_hours(db, assignment.school_id)
    if is_quiet_hours(quiet_start, quiet_end):
        return {"skipped": "quiet hours", "quiet_start": quiet_start, "quiet_end": quiet_end}
    
    # Get all submissions for this assignment
    subs_result = await db.execute(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    submissions = subs_result.scalars().all()
    
    summary = {"sent": 0, "skipped_submitted": 0, "skipped_completed": 0, "escalated": 0}
    
    for sub in submissions:
        if sub.state in (SubmissionState.COMPLETED, SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED):
            summary["skipped_submitted"] += 1
            continue
        
        if sub.state == SubmissionState.BLOCKED:
            # Escalate to teacher
            reminder = Reminder(
                assignment_id=assignment_id,
                target_student_id=sub.student_id,
                reminder_type=ReminderType.ESCALATION,
                scheduled_for=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
                state=ReminderState.SENT,
                escalation_level=1,
                message_text=f"Student is blocked on assignment: {assignment.title}. Reason: {sub.blocked_reason or 'Not specified'}"
            )
            db.add(reminder)
            summary["escalated"] += 1
            await log_event(db, event_type="reminder.escalated", school_id=assignment.school_id,
                          resource_type="submission", resource_id=sub.id,
                          details={"student_id": str(sub.student_id), "blocked_reason": sub.blocked_reason})
            continue
        
        # NOT_STARTED or IN_PROGRESS - send reminder
        is_overdue = assignment.due_date and assignment.due_date < datetime.now(timezone.utc)
        reminder = Reminder(
            assignment_id=assignment_id,
            target_student_id=sub.student_id,
            reminder_type=ReminderType.OVERDUE if is_overdue else ReminderType.UPCOMING,
            scheduled_for=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
            state=ReminderState.SENT,
            message_text=f"{'OVERDUE: ' if is_overdue else ''}Reminder for assignment: {assignment.title}"
        )
        db.add(reminder)
        summary["sent"] += 1
        await log_event(db, event_type="reminder.sent", school_id=assignment.school_id,
                      resource_type="submission", resource_id=sub.id,
                      details={"student_id": str(sub.student_id), "is_overdue": is_overdue})
    
    return summary

async def process_all_active_reminders(db: AsyncSession) -> dict:
    """Process reminders for all active assignments."""
    result = await db.execute(
        select(Assignment).where(Assignment.state == AssignmentState.ACTIVE)
    )
    assignments = result.scalars().all()
    
    results = {}
    for assignment in assignments:
        results[str(assignment.id)] = await process_reminders_for_assignment(db, assignment.id)
    
    return results
