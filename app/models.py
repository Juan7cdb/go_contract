from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, server_default='{}')
    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Stripe Customer (lazy-created on first checkout; one Customer per User).
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")
    contracts: Mapped[List["Contract"]] = relationship(back_populates="user")
    drafts: Mapped[List["ContractDraft"]] = relationship(back_populates="user")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user")

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    contracts_included: Mapped[int] = mapped_column(Integer, nullable=False)
    time_subscription: Mapped[str] = mapped_column(String(50)) # e.g., "monthly", "yearly"
    # Stripe Price/Product identifiers (nullable: e.g., Free plan has no Stripe price).
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    stripe_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # 'credit_pack' (one-time) or 'subscription' (recurring).
    plan_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="subscription", default="subscription"
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="usd", default="usd"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(100))
    start_subscription: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_subscription: Mapped[datetime] = mapped_column(DateTime)
    # Stripe subscription mirror columns. Nullable because legacy/Free rows
    # may not have a Stripe Subscription object.
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    # 'active' | 'past_due' | 'canceled' | 'incomplete' | etc.
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="active", default="active"
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    payments: Mapped[List["Payment"]] = relationship(back_populates="subscription")

class TemplateContract(Base):
    __tablename__ = "template_contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rules: Mapped[Optional[str]] = mapped_column(Text)
    steps_config: Mapped[Optional[dict]] = mapped_column(JSON)
    contract_template_url: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contracts: Mapped[List["Contract"]] = relationship(back_populates="template")
    agents: Mapped[List["Agent"]] = relationship(back_populates="template")
    drafts: Mapped[List["ContractDraft"]] = relationship(back_populates="template")

class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_contracts.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="completed", index=True) # draft, in_progress, completed
    form_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_content: Mapped[Optional[str]] = mapped_column(Text)
    contract_url: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="contracts")
    template: Mapped["TemplateContract"] = relationship(back_populates="contracts")

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_contracts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template: Mapped["TemplateContract"] = relationship(back_populates="agents")

class ContractDraft(Base):
    __tablename__ = "contract_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_contracts.id"), nullable=False, index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    form_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="drafts")
    template: Mapped["TemplateContract"] = relationship(back_populates="drafts")


class Payment(Base):
    """Audit row for every Stripe charge (one-time pack or subscription invoice).

    Created by the webhook handlers in `app/services/billing_handlers.py`.
    UNIQUE constraints on the three Stripe identifiers (intent / invoice /
    checkout session) prevent double-counting when Stripe retries an event.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("plans.id"), nullable=True)
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_checkout_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="usd", default="usd"
    )
    # 'succeeded' | 'failed' | 'pending' | 'refunded'
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    credits_granted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    # 'credit_pack' | 'subscription_first' | 'subscription_renewal'
    payment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="payments")
    plan: Mapped[Optional["Plan"]] = relationship(back_populates="payments")
    subscription: Mapped[Optional["Subscription"]] = relationship(back_populates="payments")


class StripeEvent(Base):
    """Idempotency log of every webhook event we've already processed.

    Stripe may retry the same event many times. The PK = `event.id` (evt_*)
    plus a check-then-insert in the webhook handler guarantees each event
    runs its side effects exactly once.
    """
    __tablename__ = "stripe_events"

    # Stripe `evt_xxxxx`. Acts as the PK and idempotency key.
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
