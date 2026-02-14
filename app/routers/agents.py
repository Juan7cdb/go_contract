"""Agents router for AI agents management and chat."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.client import get_supabase_client
from app.dependencies.auth import get_current_user, TokenPayload
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
    current_user: TokenPayload = Depends(get_current_user),
    template_id: Optional[str] = Query(None, description="Filter by template"),
):
    """
    List all available AI agents.
    
    Returns all agents that can be used for chat or contract assistance.
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("agents").select("*", count="exact")
        
        if template_id:
            query = query.eq("template_id", template_id)
        
        response = query.order("title").execute()
        
        return AgentListResponse(
            agents=[AgentResponse(**a) for a in response.data],
            total=response.count or len(response.data)
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
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get a specific AI agent by ID.
    
    Returns the agent details (prompt is included for transparency).
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("agents").select("*").eq("id", agent_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        return AgentResponse(**response.data)
        
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
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Chat with an AI agent.
    
    Send a message to the agent and receive a response.
    The agent uses its specific prompt/personality for responses.
    """
    supabase = get_supabase_client()
    
    try:
        # Get agent prompt
        agent = supabase.table("agents").select("*").eq("id", request.agent_id).single().execute()
        
        if not agent.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        # Chat with AI using agent's prompt
        response_text = await ai_service.chat_with_agent(
            message=request.message,
            agent_prompt=agent.data["prompt"],
            history=request.history
        )
        
        logger.info(f"Chat with agent {request.agent_id} for user {current_user.sub}")
        
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
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Chat with an AI agent (streaming response).
    
    Send a message and receive a streaming response for real-time display.
    """
    supabase = get_supabase_client()
    
    try:
        # Get agent prompt
        agent = supabase.table("agents").select("*").eq("id", request.agent_id).single().execute()
        
        if not agent.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        async def generate():
            async for chunk in ai_service.chat_with_agent_stream(
                message=request.message,
                agent_prompt=agent.data["prompt"],
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
