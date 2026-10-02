from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.reminder import Reminder
from app.services.reminder_service import process_all_active_reminders
from app.services.audit_service import log_event
import uuid
from typing import Optional

router = APIRouter()

@router.post("/trigger")
async def trigger_reminders(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    results = await process_all_active_reminders(db)
    await log_event(db, "reminders.triggered_manual", school_id=current_user.school_id,
                    actor_id=current_user.id, details={"results": str(results)})
    await db.commit()
    return {"message": "Reminders processed", "results": results}

@router.get("")
async def list_reminders(
    assignment_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Reminder)
    if assignment_id:
        query = query.where(Reminder.assignment_id == assignment_id)
    query = query.order_by(Reminder.created_at.desc()).limit(100)
    
    result = await db.execute(query)
    return [{
        "id": str(r.id), "assignment_id": str(r.assignment_id),
        "target_student_id": str(r.target_student_id),
        "reminder_type": r.reminder_type.value, "state": r.state.value,
        "message_text": r.message_text, "sent_at": str(r.sent_at) if r.sent_at else None,
        "created_at": str(r.created_at)
    } for r in result.scalars().all()]
