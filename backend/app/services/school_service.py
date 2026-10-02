import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.school import School

async def get_school(db: AsyncSession, school_id: uuid.UUID):
    result = await db.execute(select(School).where(School.id == school_id))
    return result.scalar_one_or_none()

async def update_school(db: AsyncSession, school_id: uuid.UUID, data: dict):
    school = await get_school(db, school_id)
    if school:
        for k, v in data.items():
            setattr(school, k, v)
        await db.commit()
        await db.refresh(school)
    return school
