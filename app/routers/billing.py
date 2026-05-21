"""Billing router — Stripe Checkout / Portal / Payments / Webhook endpoints.

Endpoints:
- `POST /checkout-session` (Phase 3): create a hosted Stripe Checkout
  Session for a plan.
- `POST /webhook` (Phase 4): receive signed Stripe events, verify HMAC
  over the raw body, and dispatch to the handlers in
  `app/services/billing_handlers.py`. Idempotent via the `stripe_events`
  table (PK = Stripe `event.id`).

Auth: Bearer (via `get_current_user`) for checkout. The webhook is
unauthenticated (signed by Stripe) — DO NOT add a `Depends(get_current_user)`
to it.

Source of truth: `thoughts/juandavid/plans/2026-05-20-stripe-monetization-plan.md`.
"""
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Payment, Plan, StripeEvent, User
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PaymentResponse,
    PortalSessionResponse,
)
from app.services import billing_handlers
from app.services.stripe_service import get_or_create_customer, stripe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# Map of Stripe event type → handler. Aliases (e.g. `invoice.payment_succeeded`
# in addition to `invoice.paid`) point at the same coroutine.
EVENT_HANDLERS = {
    "checkout.session.completed": billing_handlers.handle_checkout_completed,
    "invoice.paid": billing_handlers.handle_invoice_paid,
    "invoice.payment_succeeded": billing_handlers.handle_invoice_paid,
    "invoice.payment_failed": billing_handlers.handle_invoice_failed,
    "customer.subscription.created": billing_handlers.handle_subscription_updated,
    "customer.subscription.updated": billing_handlers.handle_subscription_updated,
    "customer.subscription.deleted": billing_handlers.handle_subscription_deleted,
    "charge.refunded": billing_handlers.handle_charge_refunded,
}


def _event_to_dict(event: object) -> dict:
    """Serialize a Stripe Event to a plain JSON-safe dict for storage.

    Stripe SDK objects implement `to_dict_recursive()`; some test mocks
    don't, so we fall back through several strategies.
    """
    to_dict_recursive = getattr(event, "to_dict_recursive", None)
    if callable(to_dict_recursive):
        try:
            return to_dict_recursive()
        except Exception:  # noqa: BLE001 - best-effort
            pass
    if isinstance(event, dict):
        return dict(event)
    # Last resort: round-trip via JSON if it's a StripeObject-like.
    try:
        return json.loads(str(event))
    except Exception:  # noqa: BLE001 - best-effort
        return {}


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout Session for the requested plan.

    Logic:
    - Look up the active Plan by id.
    - Reject the Free plan (no `stripe_price_id`) with a 400.
    - Ensure the user has a Stripe Customer (lazy-create if missing).
    - `mode = "payment"` for credit packs (one-time) and `"subscription"`
      for recurring plans.
    - Attach `metadata` so the webhook can credit the right user/plan,
      replicated under `subscription_data.metadata` when applicable so
      it propagates onto the created Subscription / Invoice objects.
    - An `idempotency_key` keyed by user+plan+timestamp(sec) protects
      against accidental double-clicks (Stripe will return the same
      Session for repeated calls within the second).
    """
    # 1. Lookup plan and validate it's purchasable.
    plan = await db.scalar(
        select(Plan).where(Plan.id == payload.plan_id, Plan.is_active.is_(True))
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    if not plan.stripe_price_id:
        # Free plan (or otherwise unconfigured) cannot be checked out.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free plan cannot be purchased",
        )

    # 2. Ensure Stripe Customer exists for this user.
    customer_id = await get_or_create_customer(current_user, db)

    # 3. Build the Session payload.
    mode = "payment" if plan.plan_type == "credit_pack" else "subscription"

    metadata = {
        "user_id": str(current_user.id),
        "plan_id": str(plan.id),
        "plan_type": plan.plan_type,
        # `contracts_included` is the credits granted per purchase
        # (one-time for packs, per-period for subscriptions). The webhook
        # uses this to top up `User.credits_remaining`.
        "credits_granted": str(plan.contracts_included),
    }

    # Derive success/cancel URLs from the request Origin so users return to
    # the same frontend they came from (localhost / vercel / app.gocontract.us).
    # Falls back to settings if Origin is missing or not in the allowed list.
    origin = request.headers.get("origin", "").rstrip("/")
    allowed = settings.allowed_origins_list
    base_url = origin if origin in allowed else settings.FRONTEND_URL.rstrip("/")
    success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/billing/cancel"

    session_kwargs: dict = {
        "mode": mode,
        "customer": customer_id,
        "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }

    # For subscriptions, replicate metadata on subscription_data so it
    # propagates onto the resulting Stripe Subscription + every Invoice.
    if mode == "subscription":
        session_kwargs["subscription_data"] = {"metadata": metadata}

    idempotency_key = f"checkout_{current_user.id}_{plan.id}_{int(time.time())}"

    try:
        session = stripe.checkout.Session.create(
            **session_kwargs,
            idempotency_key=idempotency_key,
        )
    except stripe.error.StripeError as exc:
        # Surface Stripe API failures with a 502 so the client knows it's
        # an upstream issue, not a bug in the request.
        logger.error(
            "stripe_checkout_session_failed",
            extra={
                "user_id": current_user.id,
                "plan_id": plan.id,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stripe Checkout session",
        ) from exc

    logger.info(
        "stripe_checkout_session_created",
        extra={
            "user_id": current_user.id,
            "plan_id": plan.id,
            "session_id": session.id,
            "mode": mode,
        },
    )

    return CheckoutSessionResponse(url=session.url, session_id=session.id)


@router.post("/portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalSessionResponse:
    """Create a Stripe Billing Portal session for the current user.

    The Portal is Stripe-hosted and lets the user manage their
    subscription (cancel / resume / swap plan), update payment methods,
    download invoices, etc. We hand back the `url`; the client redirects
    via `window.location.href = url`.

    A Stripe Customer is required to open the Portal. We call
    `get_or_create_customer` so users who have never checked out can
    still open the Portal — they'll just see an empty state, which is
    the graceful UX we want.
    """
    customer_id = await get_or_create_customer(current_user, db)

    try:
        origin = request.headers.get("origin", "").rstrip("/")
        allowed = settings.allowed_origins_list
        base_url = origin if origin in allowed else settings.FRONTEND_URL.rstrip("/")
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{base_url}/plans",
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "stripe_portal_session_failed",
            extra={
                "user_id": current_user.id,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stripe Billing Portal session",
        ) from exc

    logger.info(
        "stripe_portal_session_created",
        extra={"user_id": current_user.id, "session_id": session.id},
    )

    return PortalSessionResponse(url=session.url)


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Payment]:
    """List the current user's Payment rows, most recent first.

    Powers the Plans > Payment History tab. Returns at most 100 rows
    per page (`limit` clamped). Each row was written by a webhook
    handler in `app/services/billing_handlers.py`.
    """
    result = await db.scalars(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive and dispatch Stripe webhook events.

    Pipeline:
    1. Read RAW body (`await request.body()`) — never parse via Pydantic
       because the HMAC signature is computed over the exact bytes Stripe
       sent.
    2. Verify signature via `stripe.Webhook.construct_event`. 400 on
       invalid payload or invalid signature.
    3. Idempotency: SELECT `stripe_events` by `event.id`. If a row
       exists, return `{"duplicate": True}` immediately — side effects
       have already run for this Stripe event ID.
    4. Insert the `StripeEvent` row (within the request transaction).
    5. Dispatch to the handler for `event.type`. Unknown types are
       logged and ignored (no error).
    6. Return `{"received": True}`. The `get_db` dependency commits on
       yield. If any handler raises, `get_db` rolls back atomically and
       Stripe will retry.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Malformed body.
        logger.warning("stripe_webhook_invalid_payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("stripe_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = (
        event["id"] if isinstance(event, dict) else getattr(event, "id", None)
    )
    event_type = (
        event["type"] if isinstance(event, dict) else getattr(event, "type", None)
    )
    data_object = None
    data = event["data"] if isinstance(event, dict) else getattr(event, "data", None)
    if isinstance(data, dict):
        data_object = data.get("object")
    elif data is not None:
        data_object = getattr(data, "object", None)

    logger.info(
        "stripe_event_received",
        extra={"event_id": event_id, "event_type": event_type},
    )

    # Idempotency: check + insert. We do a check-then-insert (rather than
    # blind insert + IntegrityError) so we don't poison the outer
    # transaction with a flush error.
    existing = await db.get(StripeEvent, event_id)
    if existing is not None:
        logger.info(
            "stripe_event_duplicate",
            extra={"event_id": event_id, "event_type": event_type},
        )
        return {"duplicate": True}

    db.add(
        StripeEvent(
            id=event_id,
            event_type=event_type,
            payload=_event_to_dict(event),
        )
    )

    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.info(
            "stripe_event_unhandled",
            extra={"event_id": event_id, "event_type": event_type},
        )
        return {"received": True, "handled": False}

    logger.info(
        "stripe_event_dispatching",
        extra={"event_id": event_id, "event_type": event_type},
    )
    # Let exceptions propagate so `get_db` rolls back the StripeEvent
    # insert too — that way Stripe will retry and we don't end up with a
    # processed-flag without the matching side effect.
    await handler(data_object, db)

    return {"received": True, "handled": True}
