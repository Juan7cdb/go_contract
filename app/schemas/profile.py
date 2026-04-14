"""Profile schemas matching Supabase profiles table."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ProfileBase(BaseModel):
    """Base profile schema."""
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr


class ProfileCreate(ProfileBase):
    """Schema for creating a profile (used after registration)."""
    id: str  # UUID from auth.users


class ProfileUpdate(BaseModel):
    """Schema for updating a profile - all fields optional."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    preferences: Optional[Dict[str, Any]] = None


class ProfileResponse(BaseModel):
    """Schema for profile response."""
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfilePublic(BaseModel):
    """Public profile info (limited fields)."""
    id: str
    first_name: str
    last_name: str
