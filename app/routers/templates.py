"""Template contracts router for contract templates management."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models import User, TemplateContract
from app.dependencies.auth import get_current_user
from app.schemas.template_contract import (
    TemplateContractResponse,
    TemplateContractListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Contract Templates"])


@router.get("/", response_model=TemplateContractListResponse)
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search in title or description"),
):
    """
    List all available contract templates.
    """
    try:
        query = select(TemplateContract)
        
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    TemplateContract.title.ilike(search_filter),
                    TemplateContract.description.ilike(search_filter)
                )
            )
        
        result = await db.execute(query.order_by(TemplateContract.title))
        templates = result.scalars().all()
        
        return TemplateContractListResponse(
            templates=[
                TemplateContractResponse(
                    id=str(t.id),
                    title=t.title,
                    description=t.description,
                    rules=t.rules,
                    category=t.category,
                    subcategory=t.subcategory,
                    created_at=t.created_at
                ) for t in templates
            ],
            total=len(templates)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific contract template by ID.
    """
    try:
        t_id = int(template_id)
        result = await db.execute(select(TemplateContract).where(TemplateContract.id == t_id))
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return TemplateContractResponse(
            id=str(template.id),
            title=template.title,
            description=template.description,
            rules=template.rules,
            category=template.category,
            subcategory=template.subcategory,
            created_at=template.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching template"
        )
