from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.school import School
from app.schemas.school import SchoolResponse, UpdateSchoolRequest

router = APIRouter()

@router.get("/mine", response_model=SchoolResponse)
async def get_my_school(current_user: User = Depends(require_role(UserRole.ADMIN)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.id == current_user.school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school

@router.put("/mine", response_model=SchoolResponse)
async def update_my_school(data: UpdateSchoolRequest, current_user: User = Depends(require_role(UserRole.ADMIN)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.id == current_user.school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    if data.name:
        school.name = data.name
    if data.address:
        school.address = data.address
    if data.timezone:
        school.timezone = data.timezone
        
    return school
