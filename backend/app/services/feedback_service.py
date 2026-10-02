import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.feedback import Feedback
from app.models.enums import FeedbackAction, SubmissionState
from app.services.submission_service import update_submission_state

async def create_feedback(db: AsyncSession, submission_id: uuid.UUID, teacher_id: uuid.UUID, content: str, action: FeedbackAction):
    feedback = Feedback(submission_id=submission_id, teacher_id=teacher_id, content=content, action=action)
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    if action == FeedbackAction.REVISION_REQUEST:
        await update_submission_state(db, submission_id, SubmissionState.REVISION_REQUESTED)
    elif action == FeedbackAction.APPROVAL:
        await update_submission_state(db, submission_id, SubmissionState.COMPLETED)
        
    return feedback

async def list_feedback(db: AsyncSession, submission_id: uuid.UUID):
    result = await db.execute(select(Feedback).where(Feedback.submission_id == submission_id))
    return result.scalars().all()
