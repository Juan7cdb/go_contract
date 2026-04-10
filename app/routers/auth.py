"""Authentication router for user registration, login, and session management."""
import logging
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token
)
from app.models import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordUpdate,
    AuthResponse,
)
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user in PostgreSQL.
    """
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
            
        # Create new user
        new_user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            credits_remaining=5  # Default free credits
        )
        
        db.add(new_user)
        await db.flush() # To get the id
        
        access_token = create_access_token(subject=new_user.id)
        
        logger.info(f"New user registered: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token="not_implemented_yet", # We'll add this later if needed
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": str(new_user.id),
                "email": new_user.email,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Registration error for {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.
    """
    try:
        # Get user
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            
        access_token = create_access_token(subject=user.id)
        
        logger.info(f"User logged in: {credentials.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token="not_implemented_yet",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login error for {credentials.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login. Please try again."
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh tokens (Placeholder).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented"
    )


@router.post("/logout", response_model=AuthResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout placeholder (handled client-side by dropping the JWT).
    """
    return AuthResponse(message="Successfully logged out")


@router.post("/password-reset", response_model=AuthResponse)
async def request_password_reset(request: PasswordResetRequest):
    """
    Password reset email (Placeholder).
    """
    return AuthResponse(message="If an account exists, a password reset email has been sent")


@router.post("/password-update", response_model=AuthResponse)
async def update_password(
    request: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update password for authenticated user.
    """
    try:
        # Verify current password before allowing update
        if not verify_password(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        current_user.hashed_password = get_password_hash(request.new_password)
        db.add(current_user)
        
        logger.info(f"Password updated for user: {current_user.id}")
        return AuthResponse(message="Password updated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update password"
        )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "credits_remaining": current_user.credits_remaining,
        "created_at": current_user.created_at
    }
