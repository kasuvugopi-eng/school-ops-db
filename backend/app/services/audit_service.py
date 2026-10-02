import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent

async def log_event(
    db: AsyncSession,
    event_type: str,
    school_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    details: dict | None = None,
    correlation_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    actor_type: str = "user"
) -> AuditEvent:
    
    if not correlation_id:
        correlation_id = uuid.uuid4()
        
    event = AuditEvent(
        correlation_id=correlation_id,
        school_id=school_id,
        actor_id=actor_id,
        actor_type=actor_type,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(event)
    await db.flush()
    return event
