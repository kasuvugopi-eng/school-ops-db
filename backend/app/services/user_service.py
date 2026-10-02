import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.enums import UserRole
from app.models.student_enrollment import StudentEnrollment

async def list_teachers(db: AsyncSession, school_id: uuid.UUID):
    result = await db.execute(select(User).where(User.school_id == school_id, User.role == UserRole.TEACHER))
    return result.scalars().all()

async def list_students(db: AsyncSession, school_id: uuid.UUID, class_id: uuid.UUID = None):
    query = select(User).where(User.school_id == school_id, User.role == UserRole.STUDENT)
    if class_id:
        query = query.join(StudentEnrollment).where(StudentEnrollment.class_id == class_id)
    result = await db.execute(query)
    return result.scalars().all()

async def list_guardians(db: AsyncSession, school_id: uuid.UUID):
    result = await db.execute(select(User).where(User.school_id == school_id, User.role == UserRole.GUARDIAN))
    return result.scalars().all()

async def get_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_students_for_class(db: AsyncSession, class_id: uuid.UUID):
    result = await db.execute(
        select(User).join(StudentEnrollment).where(StudentEnrollment.class_id == class_id, User.role == UserRole.STUDENT)
    )
    return result.scalars().all()
