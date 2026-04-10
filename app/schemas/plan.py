"""Plan schemas matching Supabase plans table."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlanBase(BaseModel):
    """Base plan schema."""
    title: str = Field(..., max_length=100)
    description: str
    price: float = Field(..., ge=0)
    time_subscription: str = Field(..., max_length=50, description="Subscription period, e.g. 'monthly', 'yearly'")


class PlanCreate(PlanBase):
    """Schema for creating a plan (admin only)."""
    pass


class PlanUpdate(BaseModel):
    """Schema for updating a plan."""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    time_subscription: Optional[str] = Field(None, max_length=50)


class PlanResponse(PlanBase):
    """Schema for plan response."""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    """Schema for list of plans."""
    plans: list[PlanResponse]
    total: int
