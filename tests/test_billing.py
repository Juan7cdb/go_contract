"""Tests for Stripe webhook handlers and the `/billing/webhook` dispatcher.

These tests avoid hitting the network and avoid spinning up a real
database — instead they:
1. Patch `stripe.Webhook.construct_event` to bypass HMAC verification
   and return a fake `event` object the dispatcher will process.
2. Override the FastAPI `get_db` dependency with a fake async session
   that records `add()` calls and serves `get()` / `scalar()` from an
   in-memory dict.

Phase 4 of `thoughts/juandavid/plans/2026-05-20-stripe-monetization-plan.md`.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import Payment, Plan, StripeEvent, Subscription, User
from app.routers import billing as billing_router
from tests.conftest import FakeAsyncSession


@pytest.fixture
def fake_session() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def client(fake_session: FakeAsyncSession):
    """TestClient with `get_db` overridden to yield our fake session."""

    async def _override_get_db():
        yield fake_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------------------------------- #
# Event builders                                                              #
# --------------------------------------------------------------------------- #


def make_event(event_id: str, event_type: str, obj: dict) -> SimpleNamespace:
    """Build a fake `stripe.Event`-shaped object.

    The dispatcher reads `event.id`, `event.type`, `event.data.object`,
    so a SimpleNamespace is sufficient.
    """
    return SimpleNamespace(
        id=event_id,
        type=event_type,
        data=SimpleNamespace(object=obj),
        to_dict_recursive=lambda: {
            "id": event_id,
            "type": event_type,
            "data": {"object": obj},
        },
    )


def _post_webhook(client: TestClient, event: Any):
    """Helper to POST the webhook with `construct_event` patched to return `event`."""
    with patch.object(
        billing_router.stripe.Webhook,
        "construct_event",
        return_value=event,
    ):
        return client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=fake"},
        )


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


def test_checkout_completed_credit_pack(client: TestClient, fake_session: FakeAsyncSession):
    """Happy path: a credit-pack checkout bumps user credits + inserts Payment."""
    user = User(
        id=42,
        email="u@example.com",
        hashed_password="x",
        credits_remaining=5,
    )
    fake_session.seed(User, user)

    session_obj = {
        "id": "cs_test_123",
        "mode": "payment",
        "amount_total": 2999,
        "currency": "usd",
        "payment_intent": "pi_test_123",
        "metadata": {
            "user_id": "42",
            "plan_id": "5",
            "plan_type": "credit_pack",
            "credits_granted": "50",
        },
    }
    event = make_event("evt_1", "checkout.session.completed", session_obj)

    resp = _post_webhook(client, event)

    assert resp.status_code == 200
    assert resp.json() == {"received": True, "handled": True}
    assert user.credits_remaining == 55  # 5 + 50

    payments = [obj for obj in fake_session.added if isinstance(obj, Payment)]
    assert len(payments) == 1
    p = payments[0]
    assert p.payment_type == "credit_pack"
    assert p.status == "succeeded"
    assert p.stripe_checkout_session_id == "cs_test_123"
    assert p.stripe_payment_intent_id == "pi_test_123"
    assert p.credits_granted == 50
    assert p.amount_cents == 2999

    events = [obj for obj in fake_session.added if isinstance(obj, StripeEvent)]
    assert len(events) == 1
    assert events[0].id == "evt_1"


def test_duplicate_event_ignored(client: TestClient, fake_session: FakeAsyncSession):
    """Same event_id sent twice: second call returns duplicate, credits not doubled."""
    user = User(
        id=42,
        email="u@example.com",
        hashed_password="x",
        credits_remaining=5,
    )
    fake_session.seed(User, user)

    session_obj = {
        "id": "cs_test_dup",
        "mode": "payment",
        "amount_total": 2999,
        "currency": "usd",
        "payment_intent": "pi_test_dup",
        "metadata": {
            "user_id": "42",
            "plan_id": "5",
            "plan_type": "credit_pack",
            "credits_granted": "50",
        },
    }
    event = make_event("evt_dup", "checkout.session.completed", session_obj)

    # First call processes the event.
    resp1 = _post_webhook(client, event)
    assert resp1.status_code == 200
    assert resp1.json() == {"received": True, "handled": True}
    assert user.credits_remaining == 55

    # Second call must short-circuit on the StripeEvent row.
    resp2 = _post_webhook(client, event)
    assert resp2.status_code == 200
    assert resp2.json() == {"duplicate": True}
    # Credits unchanged.
    assert user.credits_remaining == 55


def test_invalid_signature(client: TestClient, fake_session: FakeAsyncSession):
    """SignatureVerificationError → 400."""
    err = billing_router.stripe.error.SignatureVerificationError(
        "bad sig", "t=1,v1=fake"
    )
    with patch.object(
        billing_router.stripe.Webhook,
        "construct_event",
        side_effect=err,
    ):
        resp = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=fake"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid signature"


def test_invoice_paid_subscription_renewal(
    client: TestClient, fake_session: FakeAsyncSession
):
    """invoice.paid bumps credits + inserts subscription_renewal Payment."""
    user = User(
        id=7,
        email="r@example.com",
        hashed_password="x",
        credits_remaining=10,
    )
    plan = Plan(
        id=2,
        title="Pro",
        price=29.99,
        contracts_included=15,
        time_subscription="monthly",
    )
    sub = Subscription(
        id=101,
        user_id=7,
        plan_id=2,
        start_subscription=datetime.utcnow(),
        end_subscription=datetime.utcnow(),
        stripe_subscription_id="sub_renew_1",
        status="active",
    )

    fake_session.seed(User, user)
    fake_session.seed(Plan, plan)
    fake_session.seed(Subscription, sub)
    fake_session.set_scalar("subscriptions.stripe_subscription_id", sub)
    # No existing payment for this invoice id.
    # (No handler registered → scalar returns None by default.)

    invoice_obj = {
        "id": "in_test_renew",
        "subscription": "sub_renew_1",
        "amount_paid": 2999,
        "currency": "usd",
        "payment_intent": "pi_renew",
        "period_start": 1700000000,
        "period_end": 1702592000,
    }
    event = make_event("evt_renew", "invoice.paid", invoice_obj)

    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert resp.json() == {"received": True, "handled": True}

    # 10 + 15 (plan.contracts_included)
    assert user.credits_remaining == 25

    payments = [obj for obj in fake_session.added if isinstance(obj, Payment)]
    assert len(payments) == 1
    assert payments[0].payment_type == "subscription_renewal"
    assert payments[0].stripe_invoice_id == "in_test_renew"
    assert payments[0].credits_granted == 15

    # current_period_end was synced.
    assert sub.current_period_end == datetime.utcfromtimestamp(1702592000)


def test_invoice_failed_sets_past_due(
    client: TestClient, fake_session: FakeAsyncSession
):
    """invoice.payment_failed marks Subscription.status='past_due'."""
    sub = Subscription(
        id=202,
        user_id=8,
        plan_id=2,
        start_subscription=datetime.utcnow(),
        end_subscription=datetime.utcnow(),
        stripe_subscription_id="sub_past_due",
        status="active",
    )
    fake_session.seed(Subscription, sub)
    fake_session.set_scalar("subscriptions.stripe_subscription_id", sub)

    invoice_obj = {
        "id": "in_failed_1",
        "subscription": "sub_past_due",
    }
    event = make_event("evt_failed", "invoice.payment_failed", invoice_obj)

    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert sub.status == "past_due"


def test_subscription_updated_sync(
    client: TestClient, fake_session: FakeAsyncSession
):
    """customer.subscription.updated mirrors status/cancel flag/period."""
    sub = Subscription(
        id=303,
        user_id=9,
        plan_id=2,
        start_subscription=datetime.utcnow(),
        end_subscription=datetime.utcnow(),
        stripe_subscription_id="sub_update_1",
        status="active",
        cancel_at_period_end=False,
    )
    fake_session.seed(Subscription, sub)
    fake_session.set_scalar("subscriptions.stripe_subscription_id", sub)

    sub_obj = {
        "id": "sub_update_1",
        "status": "active",
        "cancel_at_period_end": True,
        "current_period_start": 1700000000,
        "current_period_end": 1702592000,
    }
    event = make_event("evt_updated", "customer.subscription.updated", sub_obj)

    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert sub.cancel_at_period_end is True
    assert sub.current_period_end == datetime.utcfromtimestamp(1702592000)


def test_subscription_deleted_marks_canceled(
    client: TestClient, fake_session: FakeAsyncSession
):
    """customer.subscription.deleted → status='canceled', credits NOT decremented."""
    user = User(
        id=11,
        email="c@example.com",
        hashed_password="x",
        credits_remaining=30,
    )
    sub = Subscription(
        id=404,
        user_id=11,
        plan_id=2,
        start_subscription=datetime.utcnow(),
        end_subscription=datetime.utcnow(),
        stripe_subscription_id="sub_delete_1",
        status="active",
    )
    fake_session.seed(User, user)
    fake_session.seed(Subscription, sub)
    fake_session.set_scalar("subscriptions.stripe_subscription_id", sub)

    sub_obj = {"id": "sub_delete_1", "status": "canceled"}
    event = make_event("evt_deleted", "customer.subscription.deleted", sub_obj)

    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert sub.status == "canceled"
    assert sub.canceled_at is not None
    # Plan decision: credits NOT decremented on cancel.
    assert user.credits_remaining == 30


def test_charge_refunded_clamps_to_zero(
    client: TestClient, fake_session: FakeAsyncSession
):
    """charge.refunded clamps credits_remaining to 0 even if granted > remaining."""
    user = User(
        id=21,
        email="r2@example.com",
        hashed_password="x",
        credits_remaining=3,
    )
    payment = Payment(
        id=999,
        user_id=21,
        amount_cents=2999,
        currency="usd",
        status="succeeded",
        credits_granted=10,
        payment_type="credit_pack",
        stripe_payment_intent_id="pi_refund_1",
    )
    fake_session.seed(User, user)
    fake_session.seed(Payment, payment)
    # Resolve scalar(SELECT Payment WHERE stripe_payment_intent_id = ...) → our payment.
    fake_session.set_scalar("payments.stripe_payment_intent_id", payment)

    charge_obj = {
        "id": "ch_refund_1",
        "payment_intent": "pi_refund_1",
        "invoice": None,
    }
    event = make_event("evt_refund", "charge.refunded", charge_obj)

    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert payment.status == "refunded"
    # 3 - 10 → clamp to 0.
    assert user.credits_remaining == 0
