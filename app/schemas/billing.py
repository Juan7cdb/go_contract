"""Billing schemas for Stripe Checkout / Portal / Payments endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckoutSessionRequest(BaseModel):
    """Request body for POST /billing/checkout-session."""

    plan_id: int = Field(..., description="ID of the plan the user wants to buy")


class CheckoutSessionResponse(BaseModel):
    """Response from POST /billing/checkout-session.

    `url` is the Stripe-hosted Checkout URL the client should redirect
    the browser to. `session_id` (cs_*) is the Stripe Checkout Session
    identifier and is also embedded in `STRIPE_SUCCESS_URL` via the
    `{CHECKOUT_SESSION_ID}` placeholder that Stripe substitutes.
    """

    url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """Response from POST /billing/portal-session.

    `url` is the Stripe-hosted Billing Portal URL the client should
    redirect the browser to so the user can manage their subscription,
    update payment methods, view invoices, etc.
    """

    url: str


class PaymentResponse(BaseModel):
    """Single Payment row, shaped for the Plans > Payment History tab.

    Backed by `app.models.Payment`. Uses `from_attributes=True` so we
    can return ORM rows directly without an explicit `.dict()`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_cents: int
    currency: str
    payment_type: str
    status: str
    credits_granted: int
    created_at: datetime
    plan_id: Optional[int] = None
    stripe_invoice_id: Optional[str] = None


class SubscriptionCancellationResponse(BaseModel):
    """Response from POST /billing/cancel-subscription and /resume-subscription.

    Returns the post-change state of the Subscription row so the client
    can update its local view immediately, without waiting for the
    `customer.subscription.updated` webhook to land.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    cancel_at_period_end: bool
    current_period_end: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
