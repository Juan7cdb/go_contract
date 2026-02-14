"""Plans router for subscription plans management."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.client import get_supabase_client
from app.dependencies.auth import get_current_user, TokenPayload
from app.schemas.plan import PlanResponse, PlanListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("/", response_model=PlanListResponse)
async def list_plans():
    """
    List all available subscription plans.
    
    Returns all plans with pricing and duration information.
    Public endpoint - no authentication required.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("plans").select("*", count="exact").order("price").execute()
        
        return PlanListResponse(
            plans=[PlanResponse(**p) for p in response.data],
            total=response.count or len(response.data)
        )
        
    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching plans"
        )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """
    Get a specific plan by ID.
    
    Returns detailed plan information.
    Public endpoint - no authentication required.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("plans").select("*").eq("id", plan_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        return PlanResponse(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching plan {plan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching plan"
        )
