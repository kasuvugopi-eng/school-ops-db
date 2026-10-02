import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.enums import UserRole
from app.models.teacher_class import TeacherClassAssignment
from app.models.guardian_link import GuardianLink

def assert_same_school(user: User, school_id: uuid.UUID):
    if user.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resource belongs to a different school")

async def assert_teacher_of_class(db: AsyncSession, user: User, class_id: uuid.UUID):
    if user.role != UserRole.TEACHER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a teacher")
    
    result = await db.execute(
        select(TeacherClassAssignment)
        .where(TeacherClassAssignment.teacher_id == user.id, TeacherClassAssignment.class_id == class_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a teacher of this class")

def assert_student_owns_submission(user: User, submission_student_id: uuid.UUID):
    if user.id != submission_student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your submission")

async def assert_guardian_of_student(db: AsyncSession, user: User, student_id: uuid.UUID):
    if user.role != UserRole.GUARDIAN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a guardian")
        
    result = await db.execute(
        select(GuardianLink)
        .where(GuardianLink.guardian_id == user.id, GuardianLink.student_id == student_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a guardian of this student")

def assert_admin_of_school(user: User, school_id: uuid.UUID):
    if user.role != UserRole.ADMIN or user.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be admin of this school")
