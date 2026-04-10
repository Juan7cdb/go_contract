import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies.auth import get_current_user
from app.models import User, ContractDraft, TemplateContract
from app.core.database import get_db
from app.schemas.draft import (
    ContractDraftCreate,
    ContractDraftUpdate,
    ContractDraftResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drafts", tags=["Drafts"])

@router.post("/", response_model=ContractDraftResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    draft_data: ContractDraftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new contract draft."""
    try:
        # Verify template exists
        template_result = await db.execute(select(TemplateContract.id).where(TemplateContract.id == draft_data.template_id))
        if not template_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        new_draft = ContractDraft(
            user_id=current_user.id,
            template_id=draft_data.template_id,
            current_step=draft_data.current_step,
            form_data=draft_data.form_data
        )
        
        db.add(new_draft)
        await db.flush()
        
        logger.info(f"Draft created for user {current_user.id}, template {draft_data.template_id}")
        return ContractDraftResponse.model_validate(new_draft)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating draft"
        )

@router.get("/", response_model=List[ContractDraftResponse])
async def list_drafts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100)
):
    """List drafts for the current user."""
    try:
        result = await db.execute(
            select(ContractDraft)
            .where(ContractDraft.user_id == current_user.id)
            .order_by(ContractDraft.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error listing drafts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing drafts"
        )

@router.get("/{draft_id}", response_model=ContractDraftResponse)
async def get_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific draft."""
    try:
        result = await db.execute(
            select(ContractDraft)
            .where(ContractDraft.id == draft_id, ContractDraft.user_id == current_user.id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        return draft
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching draft {draft_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching draft"
        )

@router.put("/{draft_id}", response_model=ContractDraftResponse)
async def update_draft(
    draft_id: int,
    draft_data: ContractDraftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing draft."""
    try:
        result = await db.execute(
            select(ContractDraft)
            .where(ContractDraft.id == draft_id, ContractDraft.user_id == current_user.id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        
        if draft_data.current_step is not None:
            draft.current_step = draft_data.current_step
        if draft_data.form_data is not None:
            draft.form_data = draft_data.form_data
            
        await db.flush()
        
        logger.info(f"Draft {draft_id} updated for user {current_user.id}")
        return ContractDraftResponse.model_validate(draft)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft {draft_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating draft"
        )

@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a draft."""
    try:
        result = await db.execute(
            select(ContractDraft)
            .where(ContractDraft.id == draft_id, ContractDraft.user_id == current_user.id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        
        await db.delete(draft)
        
        logger.info(f"Draft {draft_id} deleted for user {current_user.id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting draft {draft_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting draft"
        )
