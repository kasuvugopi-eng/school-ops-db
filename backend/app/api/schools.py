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

from pydantic import BaseModel
from app.models.school_policy import SchoolPolicy
from app.models.enums import PolicyType

class UpdateQuietHoursRequest(BaseModel):
    start_hour: int # 0-23
    end_hour: int   # 0-23
    is_active: bool = True

@router.get("/policies/quiet-hours")
async def get_quiet_hours_policy(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(SchoolPolicy).where(
            SchoolPolicy.school_id == current_user.school_id,
            SchoolPolicy.policy_type == PolicyType.QUIET_HOURS
        )
    )
    policy = res.scalar_one_or_none()
    if policy and policy.config:
        return {
            "start_hour": policy.config.get("start", 21),
            "end_hour": policy.config.get("end", 7),
            "is_active": policy.is_active
        }
    return {"start_hour": 21, "end_hour": 7, "is_active": True}

@router.put("/policies/quiet-hours")
async def update_quiet_hours_policy(
    body: UpdateQuietHoursRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    if not (0 <= body.start_hour <= 23) or not (0 <= body.end_hour <= 23):
        raise HTTPException(status_code=400, detail="Start and End hours must be between 0 and 23.")

    res = await db.execute(
        select(SchoolPolicy).where(
            SchoolPolicy.school_id == current_user.school_id,
            SchoolPolicy.policy_type == PolicyType.QUIET_HOURS
        )
    )
    policy = res.scalar_one_or_none()
    if not policy:
        policy = SchoolPolicy(
            school_id=current_user.school_id,
            policy_type=PolicyType.QUIET_HOURS,
            config={"start": body.start_hour, "end": body.end_hour},
            is_active=body.is_active
        )
        db.add(policy)
    else:
        policy.config = {"start": body.start_hour, "end": body.end_hour}
        policy.is_active = body.is_active

    await db.commit()
    return {
        "start_hour": body.start_hour,
        "end_hour": body.end_hour,
        "is_active": policy.is_active
    }
