from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from typing import Any, Optional
from pydantic import BaseModel
import jwt
import logging

logger = logging.getLogger(__name__)

auth_scheme = HTTPBearer(auto_error=True)


class TokenPayload(BaseModel):
    """Represents the decoded JWT payload from Supabase."""
    sub: str  # User ID
    email: Optional[str] = None
    role: Optional[str] = None
    aud: Optional[str] = None
    exp: Optional[int] = None


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme)
) -> TokenPayload:
    """
    Validates the Bearer token locally using the Supabase JWT secret.
    This avoids a network call on every request, improving performance significantly.
    
    Falls back to Supabase API validation if JWT_SECRET is not configured.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Prefer local JWT validation if secret is configured
        if settings.SUPABASE_JWT_SECRET and settings.SUPABASE_JWT_SECRET != "your_jwt_secret_here":
            payload = jwt.decode(
                token.credentials,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated"
            )
            
            user_id = payload.get("sub")
            if user_id is None:
                logger.warning("JWT missing 'sub' claim")
                raise credentials_exception
            
            return TokenPayload(
                sub=user_id,
                email=payload.get("email"),
                role=payload.get("role"),
                aud=payload.get("aud"),
                exp=payload.get("exp")
            )
        else:
            # Fallback: Use Supabase client (sync, but wrapped for async)
            import asyncio
            from app.core.client import get_supabase_client
            
            supabase = get_supabase_client()
            user_response = await asyncio.to_thread(
                supabase.auth.get_user, token.credentials
            )
            
            if not user_response.user:
                raise credentials_exception
            
            return TokenPayload(
                sub=user_response.user.id,
                email=user_response.user.email,
                role=user_response.user.role
            )
            
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception("Unexpected error during authentication")
        raise credentials_exception
