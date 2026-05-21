"""Stripe SDK initialization and shared helpers.

This module is the single place where the Stripe SDK is configured.
Import `stripe` from here (not directly from `stripe`) so that the
`api_key` / `api_version` are guaranteed to be initialized before any
API call runs.

Lazy Customer creation: `get_or_create_customer` returns the
`stripe_customer_id` for a given `User`, creating it on Stripe the
first time it's requested and persisting it back to the User row.
This avoids creating phantom Customers for users who never check out.
"""

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User

# Configure the SDK at import time. Both values may be empty strings in
# environments where Stripe is not configured (local dev without Stripe);
# in that case any Stripe API call will fail with a clear AuthenticationError
# rather than silently using whatever credentials were configured elsewhere.
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION

__all__ = ["stripe", "get_or_create_customer"]


async def get_or_create_customer(user: User, db: AsyncSession) -> str:
    """Return the Stripe Customer ID for `user`, creating one if needed.

    The Customer is created lazily on the first checkout to avoid
    polluting Stripe with empty Customers for users that never pay.

    The created Customer carries metadata `{"user_id": <id>}` so we can
    cross-reference it from the Stripe Dashboard back to our DB.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )

    user.stripe_customer_id = customer.id
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return customer.id
