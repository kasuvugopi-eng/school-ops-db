from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.auth.dependencies import require_role, get_current_user
from app.auth.password import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.models.teacher_class import TeacherClassAssignment
from app.models.student_enrollment import StudentEnrollment
from app.models.grade_class import GradeClass
from app.models.invite_token import InviteToken

router = APIRouter()

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class LinkTelegramRequest(BaseModel):
    chat_id: str

@router.put("/me/password")
async def change_my_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password does not match.")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.post("/me/telegram-chat-id")
async def update_my_telegram_chat_id(
    data: LinkTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    chat_id = data.chat_id.strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail="Chat ID cannot be empty.")
    
    existing = await db.execute(select(User).where(User.telegram_chat_id == chat_id, User.id != current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This Telegram Chat ID is already linked to another account.")
    
    current_user.telegram_chat_id = chat_id
    current_user.telegram_linked_at = func.now()
    await db.commit()

    # Try sending instant Telegram confirmation message
    try:
        from app.telegram.bot import send_telegram_message
        await send_telegram_message(
            chat_id=chat_id,
            text=f"🎉 *Success!* Hello {current_user.full_name}, your SchoolOps account ({current_user.email}) is now linked to Telegram! You will receive instant notifications here."
        )
    except Exception as e:
        print(f"Warning: Failed to send Telegram confirmation message: {e}")

    return {"message": "Telegram linked successfully!", "telegram_chat_id": chat_id}


@router.get("/me/telegram", response_model=dict)
async def get_telegram_link_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(InviteToken).where(InviteToken.used_by == current_user.id))
    invite = result.scalars().first()
    
    return {
        "is_linked": current_user.telegram_chat_id is not None,
        "telegram_chat_id": current_user.telegram_chat_id,
        "linked_at": str(current_user.telegram_linked_at) if current_user.telegram_linked_at else None,
        "linking_code": invite.token if invite else None
    }

class UserListItem(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    status: str
    class_names: List[str]
    class_name: Optional[str] = None
    guardians: Optional[List[dict]] = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[UserListItem])
async def get_users(
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    users = await db.execute(
        select(User).where(User.school_id == current_user.school_id, User.role == role)
    )
    user_records = users.scalars().all()
    
    result = []
    for u in user_records:
        classes = []
        guardians = []
        if role == UserRole.TEACHER:
            res = await db.execute(
                select(GradeClass.name)
                .join(TeacherClassAssignment, GradeClass.id == TeacherClassAssignment.class_id)
                .where(
                    TeacherClassAssignment.teacher_id == u.id,
                    GradeClass.school_id == current_user.school_id
                )
            )
            classes = [row[0] for row in res.all()]
        elif role == UserRole.STUDENT:
            res = await db.execute(
                select(GradeClass.name)
                .join(StudentEnrollment, GradeClass.id == StudentEnrollment.class_id)
                .where(
                    StudentEnrollment.student_id == u.id,
                    GradeClass.school_id == current_user.school_id
                )
            )
            classes = [row[0] for row in res.all()]
            
            from app.models.guardian_link import GuardianLink
            guardian_res = await db.execute(
                select(User.full_name, GuardianLink.relationship_type)
                .join(GuardianLink, User.id == GuardianLink.guardian_id)
                .where(GuardianLink.student_id == u.id)
            )
            for row in guardian_res.all():
                guardians.append({"name": row[0], "relationship": row[1]})
        
        elif role == UserRole.GUARDIAN:
            from app.models.guardian_link import GuardianLink
            student_res = await db.execute(
                select(User.full_name, GuardianLink.relationship_type)
                .join(GuardianLink, User.id == GuardianLink.student_id)
                .where(GuardianLink.guardian_id == u.id)
            )
            for row in student_res.all():
                guardians.append({"name": row[0], "relationship": row[1]})
        
        status = "Active" if u.is_active else "Inactive"
        
        result.append(UserListItem(
            id=str(u.id),
            full_name=u.full_name,
            email=u.username if hasattr(u, "username") and u.username else u.email,
            role=u.role.value,
            status=status,
            class_names=classes,
            class_name=classes[0] if classes else None,
            guardians=guardians if (role == UserRole.STUDENT or role == UserRole.GUARDIAN) else None
        ))
        
    return result

import csv
import io
import secrets
from fastapi import UploadFile, File, Form
from app.auth.password import hash_password
from app.services.audit_service import log_event

@router.post("/bulk-import-csv")
async def bulk_import_users_csv(
    file: UploadFile = File(...),
    role: str = Form(...), # TEACHER or STUDENT
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        target_role = UserRole(role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    content = await file.read()
    text = content.decode('utf-8-sig', errors='ignore')
    reader = csv.DictReader(io.StringIO(text))

    created_users = []
    skipped_emails = []

    for row in reader:
        # Standardize CSV headers (case insensitive)
        row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        email = row_clean.get("email")
        full_name = row_clean.get("full_name") or row_clean.get("name") or row_clean.get("student_name") or row_clean.get("teacher_name")
        password = row_clean.get("password") or secrets.token_hex(4)

        if not email or not full_name:
            continue

        # Check existing user
        existing_res = await db.execute(select(User).where(User.email == email))
        if existing_res.scalar_one_or_none():
            skipped_emails.append(email)
            continue

        new_user = User(
            school_id=current_user.school_id,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=target_role,
            is_active=True
        )
        db.add(new_user)
        created_users.append({
            "email": email,
            "full_name": full_name,
            "temporary_password": password
        })

    await log_event(db, f"users.bulk_imported_{role.lower()}", school_id=current_user.school_id,
                    actor_id=current_user.id, resource_type="user",
                    details={"count": len(created_users), "skipped": len(skipped_emails)})
    await db.commit()

    return {
        "imported_count": len(created_users),
        "skipped_count": len(skipped_emails),
        "skipped_emails": skipped_emails,
        "users": created_users
    }
