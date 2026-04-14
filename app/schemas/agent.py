"""Agent schemas for AI contract configuration."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgentBase(BaseModel):
    """Base agent schema."""
    template_id: str  # UUID reference to template_contracts
    title: str = Field(..., max_length=200)
    prompt: str  # System prompt for AI


class AgentCreate(AgentBase):
    """Schema for creating an agent (admin only)."""
    pass


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    title: Optional[str] = Field(None, max_length=200)
    prompt: Optional[str] = None


class AgentResponse(AgentBase):
    """Schema for agent response."""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentWithTemplate(AgentResponse):
    """Agent with template info included."""
    template_title: Optional[str] = None


class AgentListResponse(BaseModel):
    """Schema for list of agents."""
    agents: list[AgentResponse]
    total: int


# Chat with agent
class AgentChatRequest(BaseModel):
    """Request to chat with an agent."""
    agent_id: str
    message: str = Field(..., max_length=5000)
    history: Optional[list[dict]] = None  # Previous messages


class AgentChatResponse(BaseModel):
    """Response from agent chat."""
    agent_id: str
    response: str
