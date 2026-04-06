from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    credits_remaining: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")
    contracts: Mapped[List["Contract"]] = relationship(back_populates="user")
    drafts: Mapped[List["ContractDraft"]] = relationship(back_populates="user")

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    contracts_included: Mapped[int] = mapped_column(Integer, nullable=False)
    time_subscription: Mapped[str] = mapped_column(String(50)) # e.g., "monthly", "yearly"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(100))
    start_subscription: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_subscription: Mapped[datetime] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

class TemplateContract(Base):
    __tablename__ = "template_contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_contracts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="completed") # draft, in_progress, completed
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
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template: Mapped["TemplateContract"] = relationship(back_populates="agents")

class ContractDraft(Base):
    __tablename__ = "contract_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_contracts.id"), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    form_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="drafts")
    template: Mapped["TemplateContract"] = relationship(back_populates="drafts")
