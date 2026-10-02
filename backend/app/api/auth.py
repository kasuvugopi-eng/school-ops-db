from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import RegisterSchoolRequest, TokenResponse, UserResponse
from app.services.auth_service import register_school, login, refresh_token
from app.services.audit_service import log_event
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(request: Request, data: RegisterSchoolRequest, db: AsyncSession = Depends(get_db)):
    school, admin, access_token = await register_school(db, data)
    await log_event(db, "school.registered", school_id=school.id, actor_id=admin.id, resource_type="school", resource_id=school.id, ip_address=request.client.host)
    await db.commit()
    return {"access_token": access_token, "refresh_token": "not-implemented-on-register", "token_type": "bearer", "user": admin}

@router.post("/login", response_model=TokenResponse)
async def login_endpoint(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user, access_token, refresh = await login(db, form_data.username, form_data.password)
    await log_event(db, "user.login", school_id=user.school_id, actor_id=user.id, resource_type="user", resource_id=user.id, ip_address=request.client.host)
    await db.commit()
    return {"access_token": access_token, "refresh_token": refresh, "token_type": "bearer", "user": user}

@router.post("/refresh")
async def refresh(refresh_token_str: str, db: AsyncSession = Depends(get_db)):
    new_acc, new_ref = await refresh_token(db, refresh_token_str)
    return {"access_token": new_acc, "refresh_token": new_ref, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await log_event(db, "user.logout", school_id=current_user.school_id, actor_id=current_user.id, ip_address=request.client.host)
    await db.commit()
    return {"message": "Logged out successfully"}
