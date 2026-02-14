"""Subscription schemas matching Supabase subscriptions table."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    plan_id: str  # UUID reference to plans table
    payment_method: str = Field(..., max_length=50)


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription."""
    pass  # user_id comes from authenticated user


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    plan_id: Optional[str] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    end_subscription: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: str
    user_id: str
    plan_id: str
    payment_method: str
    start_subscription: datetime
    end_subscription: datetime

    class Config:
        from_attributes = True


class SubscriptionWithPlan(SubscriptionResponse):
    """Subscription with plan details included."""
    plan_title: Optional[str] = None
    plan_price: Optional[float] = None


class SubscriptionListResponse(BaseModel):
    """Schema for list of subscriptions."""
    subscriptions: list[SubscriptionResponse]
    total: int
