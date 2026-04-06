from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.dependencies.auth import get_current_user
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_service import get_ai_service
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to chat with the LexIA Legal Agent.
    """
    try:
        ai_service = get_ai_service()
        response_text = await ai_service.chat_lexia(
            chat_request.message, 
            chat_request.history,
            db,
            current_user.id
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.exception(f"Error in chat endpoint for user {current_user.id}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")


@router.post("/stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat_stream_endpoint(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming endpoint for LexIA real-time chat supporting Tool Calling.
    """
    try:
        ai_service = get_ai_service()
        
        async def generate():
            try:
                # Need to use async generator correctly
                async for chunk in ai_service.chat_lexia_stream(
                    chat_request.message, 
                    chat_request.history,
                    db,
                    current_user.id
                ):
                    # Remove multiple newlines and wrap in SSE format
                    text = str(chunk).replace("\n", "\\n")
                    yield f"data: {text}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as inner_e:
                logger.error(f"Error yielding chunks: {inner_e}")
                yield f"data: [Error procesando la respuesta]\\n\\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        logger.exception(f"Error in streaming chat for user {current_user.id}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")
