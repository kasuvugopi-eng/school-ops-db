from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.grade_class import GradeClass
from app.models.teacher_class import TeacherClassAssignment
from app.models.student_enrollment import StudentEnrollment

router = APIRouter()

@router.get("/me/classes")
async def get_my_classes(
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(GradeClass)
        .join(TeacherClassAssignment, TeacherClassAssignment.class_id == GradeClass.id)
        .where(
            TeacherClassAssignment.teacher_id == current_user.id,
            GradeClass.school_id == current_user.school_id
        )
    )
    result = await db.execute(query)
    classes = result.scalars().all()
    
    response = []
    for c in classes:
        # Count students
        s_count = await db.execute(
            select(func.count(StudentEnrollment.id)).where(
                StudentEnrollment.class_id == c.id
            )
        )
        response.append({
            "id": str(c.id), "name": c.name, "grade_level": c.grade_level,
            "school_id": str(c.school_id), "created_at": str(c.created_at),
            "student_count": s_count.scalar() or 0
        })
    return response
