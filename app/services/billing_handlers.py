"""Stripe webhook event handlers.

Each handler is async and has signature `(stripe_object, db: AsyncSession) -> None`.
Handlers are invoked by the dispatcher in `app/routers/billing.py::stripe_webhook`
AFTER the `StripeEvent` idempotency row has been inserted and BEFORE the
session is committed by the `get_db` dependency (commit-on-yield).

Important: do NOT open new transactions here. The outer dependency
`get_db` (app/core/database.py) commits on yield / rolls back on exception,
so each handler just performs its mutations and lets the dependency
finalize the transaction. Mixing `async with db.begin():` here would
produce nested-transaction errors.

Source of truth for behavior: Phase 4 of
`thoughts/juandavid/plans/2026-05-20-stripe-monetization-plan.md`.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Plan, Subscription, User

logger = logging.getLogger(__name__)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe accessor for Stripe objects (which behave like dicts AND attrs).

    Stripe SDK objects support both `obj.foo` and `obj["foo"]`. In tests we
    often pass plain dicts or `MagicMock`s, so we normalize lookup here.
    """
    if obj is None:
        return default
    # dict-like
    if isinstance(obj, dict):
        return obj.get(key, default)
    # attribute-like
    return getattr(obj, key, default)


def _from_ts(ts: Any) -> datetime | None:
    """Convert a Stripe unix timestamp (int) to a UTC datetime, or None."""
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(ts))
    except (TypeError, ValueError):
        return None


async def handle_checkout_completed(session: Any, db: AsyncSession) -> None:
    """Process a `checkout.session.completed` event.

    Two flavors:
    - `mode == "payment"` → credit pack one-time purchase. Bumps user
      credits and inserts a `Payment` row with `payment_type='credit_pack'`.
    - `mode == "subscription"` → first subscription purchase. Upserts a
      `Subscription` row, bumps initial credits, inserts a `Payment` row
      with `payment_type='subscription_first'`.

    All metadata (user_id, plan_id, plan_type, credits_granted) is read
    from `session.metadata` which was set by the checkout endpoint.
    """
    metadata = _get(session, "metadata", {}) or {}
    user_id_raw = _get(metadata, "user_id")
    plan_id_raw = _get(metadata, "plan_id")
    plan_type = _get(metadata, "plan_type")
    credits_granted_raw = _get(metadata, "credits_granted", "0")

    if not user_id_raw or not plan_id_raw:
        logger.warning(
            "checkout_completed_missing_metadata",
            extra={"session_id": _get(session, "id")},
        )
        return

    try:
        user_id = int(user_id_raw)
        plan_id = int(plan_id_raw)
        credits_granted = int(credits_granted_raw or 0)
    except (TypeError, ValueError):
        logger.exception(
            "checkout_completed_invalid_metadata",
            extra={"session_id": _get(session, "id")},
        )
        return

    user = await db.get(User, user_id)
    if not user:
        logger.warning(
            "checkout_completed_user_not_found",
            extra={"user_id": user_id, "session_id": _get(session, "id")},
        )
        return

    plan = await db.get(Plan, plan_id)
    mode = _get(session, "mode")
    amount_cents = int(_get(session, "amount_total", 0) or 0)
    currency = _get(session, "currency", "usd") or "usd"
    session_id = _get(session, "id")
    payment_intent_id = _get(session, "payment_intent")
    stripe_subscription_id = _get(session, "subscription")

    if mode == "payment":
        # Credit pack: one-time grant.
        user.credits_remaining = (user.credits_remaining or 0) + credits_granted
        db.add(user)

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id if plan else None,
            stripe_payment_intent_id=payment_intent_id,
            stripe_checkout_session_id=session_id,
            amount_cents=amount_cents,
            currency=currency,
            status="succeeded",
            credits_granted=credits_granted,
            payment_type="credit_pack",
        )
        db.add(payment)
        logger.info(
            "checkout_completed_credit_pack",
            extra={
                "user_id": user.id,
                "plan_id": plan_id,
                "credits_granted": credits_granted,
                "session_id": session_id,
            },
        )
        return

    if mode == "subscription":
        # Upsert Subscription by stripe_subscription_id.
        subscription_row: Subscription | None = None
        if stripe_subscription_id:
            subscription_row = await db.scalar(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_subscription_id
                )
            )

        if subscription_row is None:
            # Provisional period based on the plan's time_subscription.
            # Real period_end arrives via customer.subscription.created/updated
            # and invoice.paid; this default keeps `end_subscription >= now`
            # so the UI shows the active sub immediately after checkout.
            now = datetime.utcnow()
            ts = (plan.time_subscription if plan else "monthly") or "monthly"
            days = 365 if ts == "yearly" else 30
            from datetime import timedelta
            subscription_row = Subscription(
                user_id=user.id,
                plan_id=plan.id if plan else plan_id,
                payment_method="stripe",
                start_subscription=now,
                end_subscription=now + timedelta(days=days),
                stripe_subscription_id=stripe_subscription_id,
                status="active",
            )
            db.add(subscription_row)
        else:
            subscription_row.status = "active"
            subscription_row.plan_id = plan.id if plan else subscription_row.plan_id

        # Initial credit grant (recurring credits are added per invoice).
        user.credits_remaining = (user.credits_remaining or 0) + credits_granted
        db.add(user)

        # Flush to obtain subscription_row.id for the FK on Payment.
        await db.flush()

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id if plan else None,
            subscription_id=subscription_row.id,
            stripe_payment_intent_id=payment_intent_id,
            stripe_checkout_session_id=session_id,
            amount_cents=amount_cents,
            currency=currency,
            status="succeeded",
            credits_granted=credits_granted,
            payment_type="subscription_first",
        )
        db.add(payment)
        logger.info(
            "checkout_completed_subscription_first",
            extra={
                "user_id": user.id,
                "plan_id": plan_id,
                "credits_granted": credits_granted,
                "session_id": session_id,
                "subscription_id": stripe_subscription_id,
            },
        )
        return

    logger.warning(
        "checkout_completed_unknown_mode",
        extra={"mode": mode, "session_id": session_id},
    )


async def handle_invoice_paid(invoice: Any, db: AsyncSession) -> None:
    """Process `invoice.paid` (or `invoice.payment_succeeded`).

    Bumps subscription credits monthly and inserts a `subscription_renewal`
    Payment row. Skips the first invoice if it was already accounted for
    via `checkout.session.completed` (unique constraint on `stripe_invoice_id`
    plus an explicit check).
    """
    stripe_subscription_id = _get(invoice, "subscription")
    invoice_id = _get(invoice, "id")

    if not stripe_subscription_id:
        logger.info(
            "invoice_paid_no_subscription",
            extra={"invoice_id": invoice_id},
        )
        return

    subscription_row = await db.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    if not subscription_row:
        logger.warning(
            "invoice_paid_subscription_not_found",
            extra={"stripe_subscription_id": stripe_subscription_id, "invoice_id": invoice_id},
        )
        return

    # Avoid double-counting: if a Payment already exists for this invoice
    # id (e.g. the renewal hook fires twice), bail out.
    existing = await db.scalar(
        select(Payment).where(Payment.stripe_invoice_id == invoice_id)
    )
    if existing:
        logger.info(
            "invoice_paid_already_processed",
            extra={"invoice_id": invoice_id},
        )
        return

    plan = await db.get(Plan, subscription_row.plan_id)
    credits_granted = int(plan.contracts_included) if plan else 0

    # Bump user credits for the renewal.
    user = await db.get(User, subscription_row.user_id)
    if user is not None:
        user.credits_remaining = (user.credits_remaining or 0) + credits_granted
        db.add(user)

    # Update current_period_end from invoice (best-effort: top-level
    # `period_end` first, then fall back to the first line item period).
    period_end_ts = _get(invoice, "period_end")
    period_start_ts = _get(invoice, "period_start")
    if period_end_ts is None:
        lines = _get(invoice, "lines") or {}
        data = _get(lines, "data") or []
        if data:
            first = data[0]
            period = _get(first, "period") or {}
            period_end_ts = _get(period, "end")
            period_start_ts = _get(period, "start") or period_start_ts

    period_end_dt = _from_ts(period_end_ts)
    period_start_dt = _from_ts(period_start_ts)
    if period_end_dt is not None:
        subscription_row.current_period_end = period_end_dt
        # Also keep legacy `end_subscription` aligned for older code paths.
        subscription_row.end_subscription = period_end_dt
    if period_start_dt is not None:
        subscription_row.current_period_start = period_start_dt
    subscription_row.status = "active"
    db.add(subscription_row)

    amount_cents = int(_get(invoice, "amount_paid", 0) or _get(invoice, "amount_due", 0) or 0)
    currency = _get(invoice, "currency", "usd") or "usd"
    payment_intent_id = _get(invoice, "payment_intent")

    payment = Payment(
        user_id=subscription_row.user_id,
        plan_id=subscription_row.plan_id,
        subscription_id=subscription_row.id,
        stripe_payment_intent_id=payment_intent_id,
        stripe_invoice_id=invoice_id,
        amount_cents=amount_cents,
        currency=currency,
        status="succeeded",
        credits_granted=credits_granted,
        payment_type="subscription_renewal",
    )
    db.add(payment)
    logger.info(
        "invoice_paid_processed",
        extra={
            "user_id": subscription_row.user_id,
            "subscription_id": subscription_row.id,
            "invoice_id": invoice_id,
            "credits_granted": credits_granted,
        },
    )


async def handle_invoice_failed(invoice: Any, db: AsyncSession) -> None:
    """Process `invoice.payment_failed`.

    Marks the linked subscription as `past_due`. No credit change.
    """
    stripe_subscription_id = _get(invoice, "subscription")
    invoice_id = _get(invoice, "id")

    if not stripe_subscription_id:
        logger.info(
            "invoice_failed_no_subscription",
            extra={"invoice_id": invoice_id},
        )
        return

    subscription_row = await db.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    if not subscription_row:
        logger.warning(
            "invoice_failed_subscription_not_found",
            extra={"stripe_subscription_id": stripe_subscription_id, "invoice_id": invoice_id},
        )
        return

    subscription_row.status = "past_due"
    db.add(subscription_row)
    logger.info(
        "invoice_failed_marked_past_due",
        extra={
            "subscription_id": subscription_row.id,
            "invoice_id": invoice_id,
        },
    )


async def handle_subscription_updated(sub: Any, db: AsyncSession) -> None:
    """Process `customer.subscription.updated`.

    Mirrors `status`, `cancel_at_period_end`, `current_period_end`, and
    `current_period_start` from Stripe onto our row.
    """
    stripe_subscription_id = _get(sub, "id")
    subscription_row = await db.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    if not subscription_row:
        logger.warning(
            "subscription_updated_not_found",
            extra={"stripe_subscription_id": stripe_subscription_id},
        )
        return

    new_status = _get(sub, "status")
    if new_status:
        subscription_row.status = new_status

    cancel_at_period_end = _get(sub, "cancel_at_period_end")
    if cancel_at_period_end is not None:
        subscription_row.cancel_at_period_end = bool(cancel_at_period_end)

    period_end_dt = _from_ts(_get(sub, "current_period_end"))
    if period_end_dt is not None:
        subscription_row.current_period_end = period_end_dt
        subscription_row.end_subscription = period_end_dt

    period_start_dt = _from_ts(_get(sub, "current_period_start"))
    if period_start_dt is not None:
        subscription_row.current_period_start = period_start_dt

    db.add(subscription_row)
    logger.info(
        "subscription_updated_synced",
        extra={
            "subscription_id": subscription_row.id,
            "stripe_subscription_id": stripe_subscription_id,
            "status": subscription_row.status,
        },
    )


async def handle_subscription_deleted(sub: Any, db: AsyncSession) -> None:
    """Process `customer.subscription.deleted`.

    Marks the row as `canceled` and stamps `canceled_at`. Per product
    decision (plan appendix), we DO NOT decrement credits on cancellation —
    purchased credits remain usable until consumed.
    """
    stripe_subscription_id = _get(sub, "id")
    subscription_row = await db.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    if not subscription_row:
        logger.warning(
            "subscription_deleted_not_found",
            extra={"stripe_subscription_id": stripe_subscription_id},
        )
        return

    subscription_row.status = "canceled"
    subscription_row.canceled_at = datetime.utcnow()
    db.add(subscription_row)
    logger.info(
        "subscription_deleted_marked_canceled",
        extra={
            "subscription_id": subscription_row.id,
            "stripe_subscription_id": stripe_subscription_id,
        },
    )


async def handle_charge_refunded(charge: Any, db: AsyncSession) -> None:
    """Process `charge.refunded`.

    Locates the matching `Payment` row by `stripe_payment_intent_id` (or
    `stripe_invoice_id` if the intent isn't available), marks it
    `refunded`, and clamps `User.credits_remaining = max(0, current - granted)`.

    If we cannot resolve the Payment we log and return — refusing is
    safer than guessing which user to debit.
    """
    payment_intent_id = _get(charge, "payment_intent")
    invoice_id = _get(charge, "invoice")
    charge_id = _get(charge, "id")

    if not payment_intent_id and not invoice_id:
        logger.info(
            "charge_refunded_no_link",
            extra={"charge_id": charge_id},
        )
        return

    payment: Payment | None = None
    if payment_intent_id:
        payment = await db.scalar(
            select(Payment).where(
                Payment.stripe_payment_intent_id == payment_intent_id
            )
        )
    if payment is None and invoice_id:
        payment = await db.scalar(
            select(Payment).where(Payment.stripe_invoice_id == invoice_id)
        )

    if payment is None:
        logger.warning(
            "charge_refunded_payment_not_found",
            extra={
                "charge_id": charge_id,
                "payment_intent_id": payment_intent_id,
                "invoice_id": invoice_id,
            },
        )
        return

    if payment.status == "refunded":
        logger.info(
            "charge_refunded_already_refunded",
            extra={"payment_id": payment.id, "charge_id": charge_id},
        )
        return

    payment.status = "refunded"
    db.add(payment)

    user = await db.get(User, payment.user_id)
    if user is not None:
        new_credits = (user.credits_remaining or 0) - (payment.credits_granted or 0)
        user.credits_remaining = max(0, new_credits)
        db.add(user)
        logger.info(
            "charge_refunded_processed",
            extra={
                "user_id": user.id,
                "payment_id": payment.id,
                "credits_decremented": payment.credits_granted,
                "credits_remaining": user.credits_remaining,
            },
        )
    else:
        logger.warning(
            "charge_refunded_user_not_found",
            extra={"payment_id": payment.id, "user_id": payment.user_id},
        )
