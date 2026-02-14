"""Template contracts router for contract templates management."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional

from app.core.client import get_supabase_client
from app.dependencies.auth import get_current_user, TokenPayload
from app.schemas.template_contract import (
    TemplateContractResponse,
    TemplateContractListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Contract Templates"])


@router.get("/", response_model=TemplateContractListResponse)
async def list_templates(
    current_user: TokenPayload = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search in title or description"),
):
    """
    List all available contract templates.
    
    Returns all templates that can be used to generate contracts.
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("template_contracts").select("*", count="exact")
        
        if search:
            query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
        
        response = query.order("title").execute()
        
        return TemplateContractListResponse(
            templates=[TemplateContractResponse(**t) for t in response.data],
            total=response.count or len(response.data)
        )
        
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching templates"
        )


@router.get("/{template_id}", response_model=TemplateContractResponse)
async def get_template(
    template_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get a specific contract template by ID.
    
    Returns the full template details including rules for generation.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("template_contracts").select("*").eq("id", template_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return TemplateContractResponse(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching template"
        )
