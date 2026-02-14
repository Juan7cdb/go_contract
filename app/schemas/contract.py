"""Contract schemas matching Supabase contracts table."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ContractBase(BaseModel):
    """Base contract schema."""
    template_id: str  # UUID reference to template_contracts
    title: str = Field(..., max_length=200)
    description: str


class ContractCreate(ContractBase):
    """Schema for creating a contract."""
    contract_url: str  # URL to generated contract file


class ContractUpdate(BaseModel):
    """Schema for updating a contract."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    contract_url: Optional[str] = None


class ContractResponse(BaseModel):
    """Schema for contract response."""
    id: str
    user_id: str
    template_id: str
    title: str
    description: str
    contract_url: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContractWithTemplate(ContractResponse):
    """Contract with template info included."""
    template_title: Optional[str] = None


class ContractListResponse(BaseModel):
    """Schema for list of contracts."""
    contracts: list[ContractResponse]
    total: int
    page: int
    per_page: int


# AI Generation schemas (for the generate endpoint)
class ContractGenerateRequest(BaseModel):
    """Request to generate a contract with AI."""
    template_id: str
    inputs: dict = Field(..., description="Input data for contract generation")


class ContractGenerateResponse(BaseModel):
    """Response from AI contract generation."""
    content: str
    template_id: str
    suggested_title: Optional[str] = None
