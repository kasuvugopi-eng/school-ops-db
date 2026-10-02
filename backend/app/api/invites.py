from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import require_role, get_optional_user
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.invite import CreateInviteRequest, InviteResponse, AcceptInviteRequest
from app.services.invite_service import generate_invite, validate_invite_token, accept_invite
from app.services.audit_service import log_event
from app.schemas.auth import UserResponse

router = APIRouter()

@router.post("", response_model=InviteResponse)
async def create_invite(data: CreateInviteRequest, current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)), db: AsyncSession = Depends(get_db)):
    invite = await generate_invite(
        db=db,
        school_id=current_user.school_id,
        created_by=current_user.id,
        role=data.role,
        target_class_id=data.target_class_id,
        target_student_id=data.target_student_id,
        expires_hours=data.expires_hours
    )
    await log_event(db, "invite.created", school_id=current_user.school_id, actor_id=current_user.id, resource_type="invite", resource_id=invite.id)
    return invite

@router.get("/{token}/validate")
async def validate_invite(token: str, db: AsyncSession = Depends(get_db)):
    invite = await validate_invite_token(db, token)
    return {"valid": True, "role": invite.role, "school_id": invite.school_id}

@router.post("/{token}/accept", response_model=UserResponse)
async def accept_invite_endpoint(token: str, data: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    user = await accept_invite(
        db=db,
        token_str=token,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        phone=data.phone
    )
    await log_event(db, "invite.accepted", school_id=user.school_id, actor_id=user.id, resource_type="user", resource_id=user.id)
    return user
