"""Template contract schemas matching Supabase template_contracts table."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TemplateContractBase(BaseModel):
    """Base template contract schema."""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    rules: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    contract_template_url: Optional[str] = None


class TemplateContractCreate(TemplateContractBase):
    """Schema for creating a template (admin only)."""
    pass


class TemplateContractUpdate(BaseModel):
    """Schema for updating a template."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    rules: Optional[str] = None
    contract_template_url: Optional[str] = None


class TemplateContractResponse(TemplateContractBase):
    """Schema for template contract response."""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # Allow extra fields from ORM without error
        extra = "ignore"


class TemplateContractListResponse(BaseModel):
    """Schema for list of template contracts."""
    templates: list[TemplateContractResponse]
    total: int
