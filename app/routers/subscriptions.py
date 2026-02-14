"""Subscriptions router for user subscription management."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.client import get_supabase_client
from app.dependencies.auth import get_current_user, TokenPayload
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionWithPlan,
    SubscriptionListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current", response_model=SubscriptionWithPlan)
async def get_current_subscription(
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get the current user's active subscription.
    
    Returns the user's current subscription with plan details.
    """
    supabase = get_supabase_client()
    
    try:
        # Get active subscription (end_subscription > now)
        now = datetime.utcnow().isoformat()
        response = supabase.table("subscriptions").select(
            "*, plans(title, price)"
        ).eq("user_id", current_user.sub).gte("end_subscription", now).order(
            "end_subscription", desc=True
        ).limit(1).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        sub = response.data[0]
        plan_data = sub.pop("plans", {}) or {}
        
        return SubscriptionWithPlan(
            **sub,
            plan_title=plan_data.get("title"),
            plan_price=plan_data.get("price")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching subscription"
        )


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Create a new subscription.
    
    Creates a subscription after payment is confirmed.
    """
    supabase = get_supabase_client()
    
    try:
        # Get plan details for duration
        plan = supabase.table("plans").select("*").eq("id", subscription_data.plan_id).single().execute()
        
        if not plan.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        # Calculate subscription period
        start_subscription = datetime.utcnow()
        end_subscription = start_subscription + timedelta(days=plan.data["time_subscription"])
        
        data = {
            "user_id": current_user.sub,
            "plan_id": subscription_data.plan_id,
            "payment_method": subscription_data.payment_method,
            "start_subscription": start_subscription.isoformat(),
            "end_subscription": end_subscription.isoformat(),
        }
        
        response = supabase.table("subscriptions").insert(data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )
        
        logger.info(f"Subscription created for user {current_user.sub}: plan {subscription_data.plan_id}")
        return SubscriptionResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating subscription"
        )


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    subscription_data: SubscriptionUpdate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Update an existing subscription.
    
    Can be used to change plan or payment method.
    """
    supabase = get_supabase_client()
    
    try:
        # Verify ownership
        existing = supabase.table("subscriptions").select("*").eq(
            "id", subscription_id
        ).eq("user_id", current_user.sub).single().execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        update_data = {k: v for k, v in subscription_data.model_dump().items() if v is not None}
        
        # If changing plan, recalculate end date
        if "plan_id" in update_data:
            plan = supabase.table("plans").select("time_subscription").eq(
                "id", update_data["plan_id"]
            ).single().execute()
            
            if plan.data:
                update_data["end_subscription"] = (
                    datetime.utcnow() + timedelta(days=plan.data["time_subscription"])
                ).isoformat()
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = supabase.table("subscriptions").update(update_data).eq(
            "id", subscription_id
        ).execute()
        
        logger.info(f"Subscription updated: {subscription_id}")
        return SubscriptionResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating subscription"
        )


@router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Cancel a subscription.
    
    Sets the end date to now, effectively canceling the subscription.
    """
    supabase = get_supabase_client()
    
    try:
        # Verify ownership
        existing = supabase.table("subscriptions").select("*").eq(
            "id", subscription_id
        ).eq("user_id", current_user.sub).single().execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Set end date to now
        response = supabase.table("subscriptions").update({
            "end_subscription": datetime.utcnow().isoformat()
        }).eq("id", subscription_id).execute()
        
        logger.info(f"Subscription cancelled: {subscription_id}")
        return {"message": "Subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelling subscription"
        )


@router.get("/history", response_model=SubscriptionListResponse)
async def get_subscription_history(
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get the user's subscription history.
    
    Returns all past and current subscriptions.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("subscriptions").select(
            "*", count="exact"
        ).eq("user_id", current_user.sub).order("start_subscription", desc=True).execute()
        
        return SubscriptionListResponse(
            subscriptions=[SubscriptionResponse(**s) for s in response.data],
            total=response.count or len(response.data)
        )
        
    except Exception as e:
        logger.error(f"Error fetching subscription history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching subscription history"
        )
