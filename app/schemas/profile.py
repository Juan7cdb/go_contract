"""Profile schemas matching Supabase profiles table."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import datetime


class UserPreferences(BaseModel):
    """Typed schema for user preferences stored in `users.preferences` JSON column.

    All fields are optional to remain retro-compatible with existing rows that
    may have missing or extra keys. Python field names use snake_case (matching
    the rest of the codebase) while the wire format stays camelCase via
    `alias_generator=to_camel` — the frontend payload and the persisted JSON
    column both keep their existing camelCase keys.

    `populate_by_name=True` lets callers build instances using either the
    Python name (`auto_save=True`) or the camelCase alias (`autoSave=True`).

    `extra='allow'` preserves any keys not declared here (legacy or
    forward-compat) instead of silently dropping them on serialization — both
    `GET /profile/` and `PUT /profile/` returns now keep e.g. `{"theme": "dark"}`
    intact rather than losing it the moment a response is built.
    """
    model_config = ConfigDict(
        extra='allow',
        alias_generator=to_camel,
        populate_by_name=True,
    )

    language: Optional[str] = None
    timezone: Optional[str] = None
    auto_save: Optional[bool] = None      # wire: autoSave
    ai_suggestions: Optional[bool] = None  # wire: aiSuggestions
    two_factor: Optional[bool] = None      # wire: twoFactor


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


class AuthMeResponse(ProfileResponse):
    """/auth/me response: ProfileResponse extended with credits_remaining."""
    credits_remaining: int = 0
