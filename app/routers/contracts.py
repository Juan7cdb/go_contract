"""Contracts router for contract generation and CRUD operations."""
import logging
import html
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.dependencies.auth import get_current_user, TokenPayload
from app.services.ai_service import ai_service
from app.core.client import get_supabase_client
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
    ContractGenerateRequest,
    ContractGenerateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Contracts"])


def sanitize_inputs(inputs: dict) -> dict:
    """Sanitize user inputs to prevent prompt injection."""
    sanitized = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            sanitized[key] = html.escape(value[:5000])
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_inputs(value)
        elif isinstance(value, list):
            sanitized[key] = [
                html.escape(str(v)[:1000]) if isinstance(v, str) else v
                for v in value[:50]
            ]
        else:
            sanitized[key] = html.escape(str(value)[:1000])
    return sanitized


# ============== AI Generation Endpoint ==============

@router.post("/generate", response_model=ContractGenerateResponse)
async def generate_contract(
    request: ContractGenerateRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Generate a contract using AI.
    
    Uses the template's rules and AI agent to generate a legal contract
    based on the provided input parameters.
    """
    supabase = get_supabase_client()
    
    try:
        # Get template with rules
        template = supabase.table("template_contracts").select("*").eq(
            "id", request.template_id
        ).single().execute()
        
        if not template.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Get agent for this template (if exists)
        agent = supabase.table("agents").select("*").eq(
            "template_id", request.template_id
        ).limit(1).execute()
        
        agent_prompt = agent.data[0]["prompt"] if agent.data else None
        
        # Sanitize inputs
        sanitized_inputs = sanitize_inputs(request.inputs)
        
        # Generate contract with AI
        content = await ai_service.generate_contract(
            contract_type=template.data["title"],
            inputs=sanitized_inputs,
            rules=template.data["rules"],
            agent_prompt=agent_prompt
        )
        
        logger.info(f"Contract generated for user {current_user.sub}: template {request.template_id}")
        
        return ContractGenerateResponse(
            template_id=request.template_id,
            content=content,
            suggested_title=f"{template.data['title']} - Generated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contract generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate contract. Please try again."
        )


# ============== CRUD Endpoints ==============

@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    contract_data: ContractCreate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Save a new contract.
    
    Creates a new contract record after generation.
    """
    supabase = get_supabase_client()
    
    try:
        # Verify template exists
        template = supabase.table("template_contracts").select("id").eq(
            "id", contract_data.template_id
        ).single().execute()
        
        if not template.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        data = {
            "user_id": current_user.sub,
            "template_id": contract_data.template_id,
            "title": contract_data.title,
            "description": contract_data.description,
            "contract_url": contract_data.contract_url,
        }
        
        response = supabase.table("contracts").insert(data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save contract"
            )
        
        logger.info(f"Contract saved for user {current_user.sub}: {contract_data.title}")
        return ContractResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving contract: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving contract"
        )


@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    current_user: TokenPayload = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    template_id: Optional[str] = None,
):
    """
    List all contracts for the current user.
    
    Supports pagination and filtering by template.
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("contracts").select("*", count="exact").eq("user_id", current_user.sub)
        
        if template_id:
            query = query.eq("template_id", template_id)
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
        
        response = query.execute()
        
        return ContractListResponse(
            contracts=[ContractResponse(**c) for c in response.data],
            total=response.count or 0,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error listing contracts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contracts"
        )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get a specific contract by ID.
    
    Returns the full contract details. User can only access their own contracts.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("contracts").select("*").eq(
            "id", contract_id
        ).eq("user_id", current_user.sub).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        return ContractResponse(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contract"
        )


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    contract_data: ContractUpdate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Update an existing contract.
    
    Updates only the provided fields. User can only update their own contracts.
    """
    supabase = get_supabase_client()
    
    try:
        # Filter out None values
        update_data = {k: v for k, v in contract_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = supabase.table("contracts").update(update_data).eq(
            "id", contract_id
        ).eq("user_id", current_user.sub).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        logger.info(f"Contract updated: {contract_id}")
        return ContractResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating contract"
        )


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Delete a contract.
    
    Permanently deletes the contract. User can only delete their own contracts.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("contracts").delete().eq(
            "id", contract_id
        ).eq("user_id", current_user.sub).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        logger.info(f"Contract deleted: {contract_id}")
        return {"message": "Contract deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting contract"
        )
