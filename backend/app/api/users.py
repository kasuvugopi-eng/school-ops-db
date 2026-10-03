from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.teacher_class import TeacherClassAssignment
from app.models.student_enrollment import StudentEnrollment
from app.models.grade_class import GradeClass

router = APIRouter()

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
