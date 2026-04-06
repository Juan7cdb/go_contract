from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.dependencies.auth import get_current_user
from app.models import User, Contract, ContractDraft
from app.core.database import get_db
from pydantic import BaseModel

router = APIRouter(tags=["Dashboard"])

class DashboardStats(BaseModel):
    available_contracts: int
    total_created: int
    created_this_month: int
    pending_drafts: int
    completed_this_month: int

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard metrics for the current user.
    """
    try:
        # 1. Available contracts (credits)
        available = current_user.credits_remaining
        
        # 2. Total created
        total_result = await db.execute(
            select(func.count(Contract.id)).where(Contract.user_id == current_user.id)
        )
        total_created = total_result.scalar() or 0
        
        # 3. Created this month
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        month_result = await db.execute(
            select(func.count(Contract.id)).where(
                Contract.user_id == current_user.id,
                Contract.created_at >= one_month_ago
            )
        )
        created_this_month = month_result.scalar() or 0
        
        # 4. Pending drafts
        drafts_result = await db.execute(
            select(func.count(ContractDraft.id)).where(ContractDraft.user_id == current_user.id)
        )
        pending_drafts = drafts_result.scalar() or 0
        
        # 5. Completed this month (Assuming status='completed' means finished)
        completed_result = await db.execute(
            select(func.count(Contract.id)).where(
                Contract.user_id == current_user.id,
                Contract.status == "completed",
                Contract.created_at >= one_month_ago
            )
        )
        completed_this_month = completed_result.scalar() or 0
        
        return DashboardStats(
            available_contracts=available,
            total_created=total_created,
            created_this_month=created_this_month,
            pending_drafts=pending_drafts,
            completed_this_month=completed_this_month
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard stats: {str(e)}"
        )
