import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.submission import Submission
from app.models.enums import SubmissionState

SUBMISSION_TRANSITIONS = {
    SubmissionState.NOT_STARTED: {SubmissionState.IN_PROGRESS, SubmissionState.SUBMITTED},
    SubmissionState.IN_PROGRESS: {SubmissionState.BLOCKED, SubmissionState.SUBMITTED},
    SubmissionState.BLOCKED: {SubmissionState.IN_PROGRESS},
    SubmissionState.SUBMITTED: {SubmissionState.REVISION_REQUESTED, SubmissionState.COMPLETED},
    SubmissionState.REVISION_REQUESTED: {SubmissionState.RESUBMITTED},
    SubmissionState.RESUBMITTED: {SubmissionState.COMPLETED, SubmissionState.REVISION_REQUESTED}
}

def validate_submission_transition(current: SubmissionState, target: SubmissionState) -> bool:
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
    return submission

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
