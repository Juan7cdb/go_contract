"""Authentication router for user registration, login, and session management."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from gotrue.errors import AuthApiError

from app.core.client import get_supabase_client
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordUpdate,
    AuthResponse,
)
from app.dependencies.auth import get_current_user, TokenPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user.
    
    Creates a new user account and profile in Supabase.
    Returns authentication tokens on success.
    """
    supabase = get_supabase_client()
    
    try:
        # Register user with Supabase Auth
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                }
            }
        })
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please check your information."
            )
        
        # Create profile in profiles table
        profile_data = {
            "id": response.user.id,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
        }
        
        supabase.table("profiles").insert(profile_data).execute()
        
        logger.info(f"New user registered: {user_data.email}")
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
            }
        )
        
    except AuthApiError as e:
        logger.warning(f"Registration failed for {user_data.email}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Authenticate user and return tokens.
    
    Validates credentials and returns JWT tokens for API access.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })
        
        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get user profile data
        profile = supabase.table("profiles").select("*").eq("id", response.user.id).single().execute()
        
        user_data = {
            "id": response.user.id,
            "email": response.user.email,
            "first_name": profile.data.get("first_name") if profile.data else None,
            "last_name": profile.data.get("last_name") if profile.data else None,
        }
        
        logger.info(f"User logged in: {credentials.email}")
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
            user=user_data
        )
        
    except AuthApiError as e:
        logger.warning(f"Login failed for {credentials.email}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh authentication tokens.
    
    Use the refresh token to get new access and refresh tokens.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.auth.refresh_session(request.refresh_token)
        
        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
            user={
                "id": response.user.id,
                "email": response.user.email,
            }
        )
        
    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.post("/logout", response_model=AuthResponse)
async def logout(current_user: TokenPayload = Depends(get_current_user)):
    """
    Logout the current user.
    
    Invalidates the current session.
    """
    supabase = get_supabase_client()
    
    try:
        supabase.auth.sign_out()
        logger.info(f"User logged out: {current_user.sub}")
        return AuthResponse(message="Successfully logged out")
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return AuthResponse(message="Logged out", success=True)


@router.post("/password-reset", response_model=AuthResponse)
async def request_password_reset(request: PasswordResetRequest):
    """
    Request a password reset email.
    
    Sends a password reset link to the user's email.
    """
    supabase = get_supabase_client()
    
    try:
        supabase.auth.reset_password_email(request.email)
        return AuthResponse(message="If an account exists, a password reset email has been sent")
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return AuthResponse(message="If an account exists, a password reset email has been sent")


@router.post("/password-update", response_model=AuthResponse)
async def update_password(
    request: PasswordUpdate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Update the current user's password.
    
    Requires authentication. Updates the password for the logged-in user.
    """
    supabase = get_supabase_client()
    
    try:
        supabase.auth.update_user({"password": request.new_password})
        logger.info(f"Password updated for user: {current_user.sub}")
        return AuthResponse(message="Password updated successfully")
        
    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/me")
async def get_current_user_info(current_user: TokenPayload = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns the decoded token payload and profile for the current user.
    """
    supabase = get_supabase_client()
    
    try:
        profile = supabase.table("profiles").select("*").eq("id", current_user.sub).single().execute()
        
        return {
            "id": current_user.sub,
            "email": current_user.email,
            "role": current_user.role,
            "profile": profile.data if profile.data else None
        }
    except Exception:
        return {
            "id": current_user.sub,
            "email": current_user.email,
            "role": current_user.role,
        }
