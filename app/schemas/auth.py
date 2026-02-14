"""Authentication schemas for user registration and login."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordUpdate(BaseModel):
    """Schema for password update."""
    new_password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    """Generic auth response."""
    message: str
    success: bool = True
