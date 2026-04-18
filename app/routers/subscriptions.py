"""Subscriptions router for user subscription management."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models import User, Plan, Subscription
from app.dependencies.auth import get_current_user
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionWithPlan,
    SubscriptionListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Subscriptions"])


@router.get("/current", response_model=SubscriptionWithPlan)
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's active subscription.
    """
    try:
        now = datetime.utcnow()
        # Get active subscription (end_subscription > now)
        query = select(Subscription, Plan).join(Plan).where(
            and_(
                Subscription.user_id == current_user.id,
                Subscription.end_subscription >= now
            )
        ).order_by(Subscription.end_subscription.desc()).limit(1)
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        sub, plan = row
        
        return SubscriptionWithPlan(
            id=str(sub.id),
            user_id=str(sub.user_id),
            plan_id=str(sub.plan_id),
            payment_method=sub.payment_method,
            start_subscription=sub.start_subscription,
            end_subscription=sub.end_subscription,
            plan_title=plan.title,
            plan_price=plan.price
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching subscription"
        )


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new subscription and update user credits.
    """
    try:
        plan_id = int(subscription_data.plan_id)
        # Get plan details
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        # Calculate subscription period
        start_subscription = datetime.utcnow()
        # Assuming time_subscription is in days if it's an int, but here it's a string in the model? 
        # Wait, I defined it as String(50) in models.py. I should probably use an int for days.
        # Let's assume 30 days for now if it's "monthly".
        days = 30 if "monthly" in plan.time_subscription.lower() else 365
        end_subscription = start_subscription + timedelta(days=days)
        
        new_sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            payment_method=subscription_data.payment_method,
            start_subscription=start_subscription,
            end_subscription=end_subscription
        )
        
        # Update user credits
        current_user.credits_remaining += plan.contracts_included
        
        db.add(new_sub)
        db.add(current_user)
        await db.flush()
        
        logger.info(f"Subscription created for user {current_user.id}: plan {plan.id}. Credits added: {plan.contracts_included}")
        
        return SubscriptionResponse(
            id=str(new_sub.id),
            user_id=str(new_sub.user_id),
            plan_id=str(new_sub.plan_id),
            payment_method=new_sub.payment_method,
            start_subscription=new_sub.start_subscription,
            end_subscription=new_sub.end_subscription
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating subscription"
        )


@router.get("/history", response_model=SubscriptionListResponse)
async def get_subscription_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the user's subscription history.
    """
    try:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
            .order_by(Subscription.start_subscription.desc())
        )
        subscriptions = result.scalars().all()
        
        return SubscriptionListResponse(
            subscriptions=[
                SubscriptionResponse(
                    id=str(s.id),
                    user_id=str(s.user_id),
                    plan_id=str(s.plan_id),
                    payment_method=s.payment_method,
                    start_subscription=s.start_subscription,
                    end_subscription=s.end_subscription
                ) for s in subscriptions
            ],
            total=len(subscriptions)
        )
        
    except Exception as e:
        logger.error(f"Error fetching subscription history for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching subscription history"
        )
