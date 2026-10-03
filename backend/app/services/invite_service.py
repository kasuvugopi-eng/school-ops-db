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
    relationship: str | None = None,
    expires_hours: int = 48
) -> InviteToken:
    from app.models.grade_class import GradeClass
    
    if role == UserRole.STUDENT:
        if not target_class_id:
            raise HTTPException(status_code=400, detail="target_class_id is required for STUDENT invite")
        cls_result = await db.execute(select(GradeClass).where(GradeClass.id == target_class_id))
        target_class = cls_result.scalar_one_or_none()
        if not target_class or target_class.school_id != school_id:
            from app.services.audit_service import log_event
            await log_event(db, "access.denied", school_id=school_id, actor_id=created_by, resource_type="class", resource_id=target_class_id)
            raise HTTPException(status_code=404, detail="Target class not found or access denied")
            
    if role == UserRole.GUARDIAN:
        if not target_student_id:
            raise HTTPException(status_code=400, detail="target_student_id is required for GUARDIAN invite")
        if not relationship or relationship not in ["mother", "father", "guardian", "other"]:
            raise HTTPException(status_code=400, detail="valid relationship is required for GUARDIAN invite")
        stu_result = await db.execute(select(User).where(User.id == target_student_id, User.role == UserRole.STUDENT))
        target_student = stu_result.scalar_one_or_none()
        if not target_student or target_student.school_id != school_id:
            from app.services.audit_service import log_event
            await log_event(db, "access.denied", school_id=school_id, actor_id=created_by, resource_type="user", resource_id=target_student_id)
            raise HTTPException(status_code=404, detail="Target student not found or access denied")
    
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    
    invite = InviteToken(
        school_id=school_id,
        created_by=created_by,
        token=token_str,
        role=role,
        target_class_id=target_class_id,
        target_student_id=target_student_id,
        relationship_val=relationship,
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
    
    if invite.role == UserRole.STUDENT and invite.target_class_id:
        from app.models.student_enrollment import StudentEnrollment
        existing_enrollment = await db.execute(select(StudentEnrollment).where(StudentEnrollment.student_id == user.id))
        existing_enrollment = existing_enrollment.scalar_one_or_none()
        if existing_enrollment:
            if existing_enrollment.class_id != invite.target_class_id:
                raise HTTPException(status_code=409, detail="Student is already enrolled in a different class")
        else:
            enrollment = StudentEnrollment(
                student_id=user.id,
                class_id=invite.target_class_id
            )
            db.add(enrollment)
            await db.flush()
            from app.services.audit_service import log_event
            await log_event(db, "student.enrolled", school_id=user.school_id, actor_id=user.id, resource_type="enrollment", resource_id=enrollment.id)
            
    if invite.role == UserRole.GUARDIAN and invite.target_student_id:
        from app.models.guardian_link import GuardianLink
        existing_link = await db.execute(select(GuardianLink).where(GuardianLink.guardian_id == user.id, GuardianLink.student_id == invite.target_student_id))
        existing_link = existing_link.scalar_one_or_none()
        if not existing_link:
            link = GuardianLink(
                guardian_id=user.id,
                student_id=invite.target_student_id,
                relationship_type=invite.relationship_val or "guardian",
                opted_in=False
            )
            db.add(link)
            await db.flush()
            from app.services.audit_service import log_event
            await log_event(db, "guardian.linked", school_id=user.school_id, actor_id=user.id, resource_type="guardian_link", resource_id=link.id)
    
    return user
