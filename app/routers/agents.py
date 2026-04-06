"""Agents router for AI agents management and chat."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import User, Agent
from app.dependencies.auth import get_current_user
from app.services.ai_service import ai_service
from app.schemas.agent import (
    AgentResponse,
    AgentListResponse,
    AgentChatRequest,
    AgentChatResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["AI Agents"])


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    template_id: Optional[str] = Query(None, description="Filter by template"),
):
    """
    List all available AI agents.
    """
    try:
        query = select(Agent)
        
        if template_id:
            query = query.where(Agent.template_id == int(template_id))
        
        result = await db.execute(query.order_by(Agent.title))
        agents = result.scalars().all()
        
        return AgentListResponse(
            agents=[
                AgentResponse(
                    id=str(a.id),
                    template_id=str(a.template_id),
                    title=a.title,
                    description=a.description,
                    prompt=a.prompt,
                    created_at=a.created_at
                ) for a in agents
            ],
            total=len(agents)
        )
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching agents"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific AI agent by ID.
    """
    try:
        a_id = int(agent_id)
        result = await db.execute(select(Agent).where(Agent.id == a_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        return AgentResponse(
            id=str(agent.id),
            template_id=str(agent.template_id),
            title=agent.title,
            description=agent.description,
            prompt=agent.prompt,
            created_at=agent.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching agent"
        )


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with an AI agent.
    """
    try:
        a_id = int(request.agent_id)
        result = await db.execute(select(Agent).where(Agent.id == a_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        # Chat with AI using agent's prompt
        response_text = await ai_service.chat_with_agent(
            message=request.message,
            agent_prompt=agent.prompt,
            history=request.history
        )
        
        logger.info(f"Chat with agent {request.agent_id} for user {current_user.id}")
        
        return AgentChatResponse(
            agent_id=request.agent_id,
            response=response_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agent chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )


@router.post("/chat/stream")
async def chat_with_agent_stream(
    request: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with an AI agent (streaming response).
    """
    try:
        a_id = int(request.agent_id)
        result = await db.execute(select(Agent).where(Agent.id == a_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        async def generate():
            async for chunk in ai_service.chat_with_agent_stream(
                message=request.message,
                agent_prompt=agent.prompt,
                history=request.history
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agent stream chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )
