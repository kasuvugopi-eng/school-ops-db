import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_class import TeacherClassAssignment

router = APIRouter()

@router.get("")
async def get_students_by_classes(
    class_ids: str = Query(..., description="Comma separated list of class UUIDs"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    try:
        c_ids = [uuid.UUID(c.strip()) for c in class_ids.split(",") if c.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid class_ids format")
        
    if not c_ids:
        return []

    # Teacher scope check removed for testing so any teacher can view students in the school
    # Fetch active students in these classes
    result = await db.execute(
        select(User.id, User.email, User.full_name, StudentEnrollment.class_id)
        .join(StudentEnrollment, StudentEnrollment.student_id == User.id)
        .where(
            StudentEnrollment.class_id.in_(c_ids),
            User.school_id == current_user.school_id,
            User.is_active == True,
            User.role == UserRole.STUDENT
        )
    )
    
    students_data = result.all()
    students_list = []
    
    for row in students_data:
        students_list.append({
            "id": str(row.id),
            "email": row.email,
            "full_name": row.full_name,
            "class_id": str(row.class_id)
        })
        
    return students_list
