import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.audit_event import AuditEvent
from typing import Optional

router = APIRouter()

@router.get("")
async def list_audit_events(
    event_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditEvent).where(AuditEvent.school_id == current_user.school_id)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if resource_type:
        query = query.where(AuditEvent.resource_type == resource_type)
    
    query = query.order_by(desc(AuditEvent.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    
    return [{
        "id": str(e.id), "correlation_id": str(e.correlation_id) if e.correlation_id else None,
        "event_type": e.event_type, "actor_id": str(e.actor_id) if e.actor_id else None,
        "actor_type": e.actor_type, "resource_type": e.resource_type,
        "resource_id": str(e.resource_id) if e.resource_id else None,
        "details": e.details, "created_at": str(e.created_at)
    } for e in result.scalars().all()]

@router.get("/{correlation_id}")
async def get_events_by_correlation(
    correlation_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.correlation_id == correlation_id,
            AuditEvent.school_id == current_user.school_id
        ).order_by(AuditEvent.created_at.asc())
    )
    return [{
        "id": str(e.id), "event_type": e.event_type,
        "actor_id": str(e.actor_id) if e.actor_id else None,
        "resource_type": e.resource_type,
        "resource_id": str(e.resource_id) if e.resource_id else None,
        "details": e.details, "created_at": str(e.created_at)
    } for e in result.scalars().all()]
