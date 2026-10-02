from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.auth.jwt_handler import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_optional_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User | None:
    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        
        result = await db.execute(select(User).where(User.id == user_id_str))
        user = result.scalar_one_or_none()
        return user
    except Exception:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str or payload.get("type") != "access":
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id_str))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

def require_role(*roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return current_user
    return role_checker
