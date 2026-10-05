import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import require_role
from app.auth.permissions import assert_same_school
from app.models.enums import UserRole
from app.models.user import User
from app.models.grade_class import GradeClass
from app.models.student_enrollment import StudentEnrollment
from app.models.guardian_link import GuardianLink
from app.models.announcement import Announcement
from app.services.audit_service import log_event
from app.telegram.bot import send_telegram_message

router = APIRouter()

class CreateAnnouncementBody(BaseModel):
    title: str
    message: str
    target_class_id: Optional[str] = None
    target_role: Optional[str] = "ALL"  # ALL, STUDENT, TEACHER, GUARDIAN

@router.post("")
async def create_and_broadcast_announcement(
    body: CreateAnnouncementBody,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    target_class_uuid = None
    class_name = "All Classes"
    if body.target_class_id and body.target_class_id != "ALL":
        try:
            target_class_uuid = uuid.UUID(body.target_class_id)
            cls_res = await db.execute(select(GradeClass).where(GradeClass.id == target_class_uuid))
            target_cls = cls_res.scalar_one_or_none()
            if target_cls:
                assert_same_school(current_user, target_cls.school_id)
                class_name = target_cls.name
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target_class_id format")

    # Find target users to receive Telegram Broadcast
    target_users = set()

    # Query Users
    if target_class_uuid:
        # Get students in target class
        std_res = await db.execute(
            select(User)
            .join(StudentEnrollment, StudentEnrollment.student_id == User.id)
            .where(StudentEnrollment.class_id == target_class_uuid, User.is_active == True)
        )
        students = std_res.scalars().all()
        if body.target_role in ("ALL", "STUDENT"):
            for s in students:
                target_users.add(s)

        if body.target_role in ("ALL", "GUARDIAN"):
            # Get guardians of these students
            std_ids = [s.id for s in students]
            if std_ids:
                grd_res = await db.execute(
                    select(User)
                    .join(GuardianLink, GuardianLink.guardian_id == User.id)
                    .where(GuardianLink.student_id.in_(std_ids), User.is_active == True)
                )
                for g in grd_res.scalars().all():
                    target_users.add(g)
    else:
        # All School Users
        query = select(User).where(User.school_id == current_user.school_id, User.is_active == True)
        if body.target_role and body.target_role != "ALL":
            try:
                role_enum = UserRole(body.target_role)
                query = query.where(User.role == role_enum)
            except ValueError:
                pass
        usr_res = await db.execute(query)
        for u in usr_res.scalars().all():
            target_users.add(u)

    # Save Announcement Record
    announcement = Announcement(
        school_id=current_user.school_id,
        created_by=current_user.id,
        target_class_id=target_class_uuid,
        target_role=body.target_role,
        title=body.title,
        message=body.message,
        recipient_count=len(target_users)
    )
    db.add(announcement)
    await log_event(db, "announcement.broadcasted", school_id=current_user.school_id,
                    actor_id=current_user.id, resource_type="announcement",
                    details={"title": body.title, "recipients": len(target_users)})
    await db.commit()

    # Check Quiet Hours Policy before broadcasting
    from app.services.reminder_service import get_quiet_hours, is_quiet_hours
    quiet_start, quiet_end, is_active = await get_quiet_hours(db, current_user.school_id)
    quiet_active = is_quiet_hours(quiet_start, quiet_end, is_active)

    # Broadcast via Telegram
    formatted_msg = (
        "📢 *SCHOOL ANNOUNCEMENT*\n\n"
        f"📌 *Title:* {body.title}\n"
        f"🏫 *Target:* {class_name}\n"
        f"👤 *From:* School Administration ({current_user.full_name})\n\n"
        f"{body.message}"
    )

    sent_count = 0
    if not quiet_active:
        for u in target_users:
            if u.telegram_chat_id:
                await send_telegram_message(u.telegram_chat_id, formatted_msg)
                sent_count += 1

    return {
        "id": str(announcement.id),
        "title": announcement.title,
        "recipient_count": len(target_users),
        "telegram_sent_count": sent_count,
        "quiet_hours_active": quiet_active,
        "notice": f"Quiet Hours active ({quiet_start}:00 to {quiet_end}:00). Telegram alerts muted." if quiet_active else None,
        "created_at": str(announcement.created_at)
    }

@router.get("")
async def list_announcements(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Announcement, User.full_name, GradeClass.name)
        .join(User, Announcement.created_by == User.id)
        .outerjoin(GradeClass, Announcement.target_class_id == GradeClass.id)
        .where(Announcement.school_id == current_user.school_id)
        .order_by(Announcement.created_at.desc())
    )
    announcements = []
    for ann, author_name, class_name in result.all():
        announcements.append({
            "id": str(ann.id),
            "title": ann.title,
            "message": ann.message,
            "author_name": author_name,
            "target_class_name": class_name or "All Classes",
            "target_role": ann.target_role or "ALL",
            "recipient_count": ann.recipient_count,
            "created_at": str(ann.created_at)
        })
    return announcements
