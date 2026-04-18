"""Contracts router for contract generation and CRUD operations."""
import logging
import html
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies.auth import get_current_user
from app.models import User, Contract, TemplateContract, Agent
from app.core.database import get_db
from app.services.ai_service import get_ai_service
from app.services.pdf_service import get_pdf_service
from app.services.storage_service import get_storage_service
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

@router.post("/generate", response_model=ContractGenerateResponse, summary="Generar contrato con IA")
async def generate_contract(
    request: ContractGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a contract using AI.
    """
    try:
        # Get template with rules
        template_id = int(request.template_id)
        result = await db.execute(select(TemplateContract).where(TemplateContract.id == template_id))
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Get agent for this template
        agent_result = await db.execute(select(Agent).where(Agent.template_id == template_id).limit(1))
        agent = agent_result.scalar_one_or_none()
        agent_prompt = agent.prompt if agent else None
        
        # Sanitize inputs
        sanitized_inputs = sanitize_inputs(request.inputs)
        
        # Generate contract with AI
        content = await get_ai_service().generate_contract(
            contract_type=template.title,
            inputs=sanitized_inputs,
            rules=template.rules,
            agent_prompt=agent_prompt
        )
        
        logger.info(f"Contract generated for user {current_user.id}: template {template_id}")
        
        return ContractGenerateResponse(
            template_id=str(template_id),
            content=content,
            suggested_title=f"{template.title} - Generated"
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

@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED, summary="Guardar un nuevo contrato")
async def create_contract(
    contract_data: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a new contract.
    """
    try:
        template_id = int(contract_data.template_id)
        # Verify template exists
        template_result = await db.execute(select(TemplateContract.id).where(TemplateContract.id == template_id))
        if not template_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check credits
        if current_user.credits_remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No credits remaining. Please upgrade your plan."
            )
        
        # 1. Generate PDF from the generated content
        pdf_bytes = get_pdf_service().generate_pdf_from_markdown(
            contract_data.generated_content, 
            f"Contract_{current_user.id}_{template_id}.pdf"
        )
        
        contract_url = ""
        if pdf_bytes:
            # 2. Upload to storage
            filename = f"contract_{current_user.id}_{int(func.now().tstamp()) if hasattr(func.now(), 'tstamp') else id(contract_data)}.pdf"
            # Simple unique filename
            import time
            filename = f"contract_{current_user.id}_{int(time.time())}.pdf"
            contract_url = await get_storage_service().upload_pdf(pdf_bytes, filename)

        new_contract = Contract(
            user_id=current_user.id,
            template_id=template_id,
            title=contract_data.title,
            description=contract_data.description,
            contract_url=contract_url or contract_data.contract_url,
            generated_content=contract_data.generated_content,
            form_data=contract_data.form_data or {}
        )
        
        # Deduct credit
        current_user.credits_remaining -= 1
        
        db.add(new_contract)
        db.add(current_user)
        await db.flush()
        
        logger.info(f"Contract saved for user {current_user.id}: {new_contract.title}")
        return ContractResponse(
            id=str(new_contract.id),
            user_id=str(current_user.id),
            template_id=str(template_id),
            title=new_contract.title,
            description=new_contract.description,
            contract_url=new_contract.contract_url or "",
            generated_content=new_contract.generated_content,
            form_data=new_contract.form_data,
            created_at=new_contract.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving contract: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving contract"
        )


@router.get("/", response_model=ContractListResponse, summary="Listar contratos del usuario")
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List all contracts for the current user.
    """
    try:
        query = select(Contract).where(Contract.user_id == current_user.id)
        
        if template_id:
            query = query.where(Contract.template_id == int(template_id))
        
        if status and status != "All Statuses":
            query = query.where(Contract.status == status.lower())
            
        if search:
            search_filter = f"%{search}%"
            query = query.where(func.lower(Contract.title).ilike(search_filter.lower()))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Pagination
        query = query.order_by(Contract.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        contracts = result.scalars().all()
        
        return ContractListResponse(
            contracts=[
                ContractResponse(
                    id=str(c.id),
                    user_id=str(c.user_id),
                    template_id=str(c.template_id),
                    title=c.title,
                    description=c.description,
                    contract_url=c.contract_url or "",
                    generated_content=c.generated_content,
                    form_data=c.form_data,
                    created_at=c.created_at
                ) for c in contracts
            ],
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error listing contracts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contracts"
        )


@router.get("/{contract_id}", response_model=ContractResponse, summary="Obtener detalle de contrato")
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific contract by ID.
    """
    try:
        c_id = int(contract_id)
        result = await db.execute(
            select(Contract).where(Contract.id == c_id, Contract.user_id == current_user.id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        return ContractResponse(
            id=str(contract.id),
            user_id=str(contract.user_id),
            template_id=str(contract.template_id),
            title=contract.title,
            description=contract.description,
            contract_url=contract.contract_url,
            generated_content=contract.generated_content,
            form_data=contract.form_data,
            created_at=contract.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contract"
        )


@router.put("/{contract_id}", response_model=ContractResponse, summary="Actualizar contrato existente")
async def update_contract(
    contract_id: str,
    contract_data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing contract.
    """
    try:
        c_id = int(contract_id)
        result = await db.execute(
            select(Contract).where(Contract.id == c_id, Contract.user_id == current_user.id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
            
        if contract_data.title is not None:
            contract.title = contract_data.title
        if contract_data.description is not None:
            contract.description = contract_data.description
        if contract_data.contract_url is not None:
            contract.contract_url = contract_data.contract_url
            
        db.add(contract)
        
        logger.info(f"Contract updated: {contract_id}")
        return ContractResponse(
            id=str(contract.id),
            user_id=str(contract.user_id),
            template_id=str(contract.template_id),
            title=contract.title,
            description=contract.description,
            contract_url=contract.contract_url,
            created_at=contract.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating contract"
        )


@router.delete("/{contract_id}", summary="Eliminar contrato")
async def delete_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a contract.
    """
    try:
        c_id = int(contract_id)
        result = await db.execute(
            select(Contract).where(Contract.id == c_id, Contract.user_id == current_user.id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
            
        await db.delete(contract)
        
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
