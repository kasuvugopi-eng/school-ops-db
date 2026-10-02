import secrets
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.invite_token import InviteToken
from app.models.user import User
from app.models.enums import UserRole
from app.auth.password import hash_password

async def generate_invite(
    db: AsyncSession, 
    school_id: uuid.UUID, 
    created_by: uuid.UUID, 
    role: UserRole, 
    target_class_id: uuid.UUID | None = None, 
    target_student_id: uuid.UUID | None = None, 
    expires_hours: int = 48
) -> InviteToken:
    
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    
    invite = InviteToken(
        school_id=school_id,
        created_by=created_by,
        token=token_str,
        role=role,
        target_class_id=target_class_id,
        target_student_id=target_student_id,
        expires_at=expires_at
    )
    db.add(invite)
    await db.flush()
    return invite

async def validate_invite_token(db: AsyncSession, token_str: str) -> InviteToken:
    result = await db.execute(select(InviteToken).where(InviteToken.token == token_str))
    invite = result.scalar_one_or_none()
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    if invite.used_at is not None:
        raise HTTPException(status_code=400, detail="Invite already used")
        
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")
        
    return invite

async def accept_invite(
    db: AsyncSession, 
    token_str: str, 
    email: str, 
    password: str, 
    full_name: str, 
    phone: str | None = None
) -> User:
    invite = await validate_invite_token(db, token_str)
    
    existing_user = await db.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=invite.role,
        school_id=invite.school_id
    )
    db.add(user)
    await db.flush()
    
    invite.used_at = datetime.now(timezone.utc)
    invite.used_by = user.id
    
    # Linking logic (teacher -> class, student -> class, guardian -> student) would be handled here
    # or propagated back for the caller to handle based on invite properties.
    
    return user
