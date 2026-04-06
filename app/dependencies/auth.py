from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models import User
from typing import Any, Optional
from pydantic import BaseModel
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

auth_scheme = HTTPBearer(auto_error=True)

class TokenPayload(BaseModel):
    """Represents the decoded JWT payload."""
    sub: str  # User ID (usually email or int id string)
    exp: Optional[int] = None

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates the Bearer token using our own JWT_SECRET.
    Fetches the user from the PostgreSQL database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        # user_id in payload is the User.id (int) converted to string
        query = select(User).where(User.id == int(user_id_str))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
            
        return user
            
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception(f"Unexpected error during authentication: {e}")
        raise credentials_exception
