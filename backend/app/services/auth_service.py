from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.auth import RegisterSchoolRequest
from app.models.school import School
from app.models.user import User
from app.models.enums import UserRole
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, create_refresh_token, decode_token

async def register_school(db: AsyncSession, data: RegisterSchoolRequest) -> tuple[School, User, str]:
    existing_school = await db.execute(select(School).where(School.code == data.school_code))
    if existing_school.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="School code already exists")
        
    # Allow same admin email for different schools if needed

    school = School(name=data.school_name, code=data.school_code)
    db.add(school)
    await db.flush()
    
    admin_user = User(
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        phone=data.admin_phone,
        role=UserRole.ADMIN,
        school_id=school.id
    )
    db.add(admin_user)
    await db.flush()
    
    access_token = create_access_token({"sub": str(admin_user.id), "role": admin_user.role, "school_id": str(school.id)})
    return school, admin_user, access_token

async def login(db: AsyncSession, email: str, password: str, school_code: str = None, school_name: str = None) -> tuple[User, str, str]:
    from sqlalchemy import func
    query = select(User)
    clean_school_name = (school_name or "").strip().lower()
    
    if clean_school_name:
        query = query.join(School, User.school_id == School.id).where(func.lower(School.name) == clean_school_name, User.email == email)
    elif school_code:
        query = query.join(School, User.school_id == School.id).where(School.code == school_code, User.email == email)
    else:
        query = query.where(User.email == email)
        
    result = await db.execute(query)
    users = result.scalars().all()
    
    user = None
    for u in users:
        if verify_password(password, u.password_hash):
            user = u
            break
            
    if not user:
        if clean_school_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or school name mismatch.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token({"sub": str(user.id), "role": user.role, "school_id": str(user.school_id) if user.school_id else None})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return user, access_token, refresh_token

async def refresh_token(db: AsyncSession, refresh_token_str: str) -> tuple[str, str]:
    payload = decode_token(refresh_token_str)
    user_id_str = payload.get("sub")
    
    if not user_id_str or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    result = await db.execute(select(User).where(User.id == user_id_str))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
        
    new_access = create_access_token({"sub": str(user.id), "role": user.role, "school_id": str(user.school_id) if user.school_id else None})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    
    return new_access, new_refresh
