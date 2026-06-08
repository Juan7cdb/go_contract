"""Profile schemas matching Supabase profiles table."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserPreferences(BaseModel):
    """Typed schema for user preferences stored in `users.preferences` JSON column.

    All fields are optional to remain retro-compatible with existing rows that
    may have missing or extra keys. Field names use camelCase to align with the
    payload the frontend sends today (avoids a name-translation layer).

    `extra='allow'` preserves any keys not declared here (legacy or
    forward-compat) instead of silently dropping them on serialization — both
    `GET /profile/` and `PUT /profile/` returns now keep e.g. `{"theme": "dark"}`
    intact rather than losing it the moment a response is built.
    """
    model_config = ConfigDict(extra='allow')

    language: Optional[str] = None
    timezone: Optional[str] = None
    autoSave: Optional[bool] = None
    aiSuggestions: Optional[bool] = None
    twoFactor: Optional[bool] = None


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
    preferences: Optional[UserPreferences] = None


class ProfileResponse(BaseModel):
    """Schema for profile response."""
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    avatar_url: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfilePublic(BaseModel):
    """Public profile info (limited fields)."""
    id: str
    first_name: str
    last_name: str
