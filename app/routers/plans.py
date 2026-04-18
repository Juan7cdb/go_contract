"""Plans router for subscription plans management."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Plan
from app.schemas.plan import PlanResponse, PlanListResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Plans"])


@router.get("/", response_model=PlanListResponse)
async def list_plans(db: AsyncSession = Depends(get_db)):
    """
    List all available subscription plans.
    """
    try:
        result = await db.execute(select(Plan).order_by(Plan.price))
        plans = result.scalars().all()
        
        return PlanListResponse(
            plans=[
                PlanResponse(
                    id=str(p.id),
                    title=p.title,
                    price=p.price,
                    time_subscription=p.time_subscription,
                    contracts_included=p.contracts_included,
                    created_at=p.created_at
                ) for p in plans
            ],
            total=len(plans)
        )
        
    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching plans"
        )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific plan by ID.
    """
    try:
        p_id = int(plan_id)
        result = await db.execute(select(Plan).where(Plan.id == p_id))
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        return PlanResponse(
            id=str(plan.id),
            title=plan.title,
            price=plan.price,
            time_subscription=plan.time_subscription,
            contracts_included=plan.contracts_included,
            created_at=plan.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching plan {plan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching plan"
        )
