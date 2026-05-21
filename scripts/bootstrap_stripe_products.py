"""Idempotently create the GoContract Products + Prices in Stripe.

Run this once (per Stripe account / environment) to populate the
Test-mode (or Live-mode) Stripe Dashboard with the 5 paid offerings:

  - 2 subscriptions  : Pro Monthly, Enterprise Monthly
  - 3 one-time packs : Credit Pack Small / Medium / Large

The script searches existing Products by metadata key `goc_plan_id` to
avoid creating duplicates on re-run. At the end it prints a table
mapping `plan_id` to its newly created (or pre-existing) `stripe_price_id`
that you should paste into `scripts/seed_data.py`.

Usage:
    cd backend_go_contract
    STRIPE_SECRET_KEY=sk_test_xxx python scripts/bootstrap_stripe_products.py

Prereqs:
    - `pip install stripe==10.12.0` (already in requirements.txt)
    - A valid `STRIPE_SECRET_KEY` (Test mode recommended) in env / .env
"""

import os
import sys

# Allow `from app.* import ...` when this script is run from anywhere.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import the SDK *after* sys.path is set so settings load works.
from app.services.stripe_service import stripe  # noqa: E402  (intentional)


# ---------------------------------------------------------------------------
# Source of truth: keep this table in sync with the research doc
#   thoughts/juandavid/research/2026-05-20-stripe-monetization-design.md (~lines 390-398)
# and with scripts/seed_data.py.
# Free plan (id=1) is intentionally omitted — it has no Stripe Price.
# ---------------------------------------------------------------------------
PRODUCTS = [
    {
        "plan_id": 2,
        "name": "Pro Monthly",
        "description": "Pro plan — 15 contracts per month.",
        "amount_cents": 2999,  # $29.99
        "currency": "usd",
        "recurring": {"interval": "month"},
        "credits_granted": 15,
        "plan_type": "subscription",
    },
    {
        "plan_id": 3,
        "name": "Enterprise Monthly",
        "description": "Enterprise plan — 1000 contracts per month.",
        "amount_cents": 9999,  # $99.99
        "currency": "usd",
        "recurring": {"interval": "month"},
        "credits_granted": 1000,
        "plan_type": "subscription",
    },
    {
        "plan_id": 4,
        "name": "Credit Pack Small",
        "description": "10 one-time credits.",
        "amount_cents": 999,  # $9.99
        "currency": "usd",
        "recurring": None,
        "credits_granted": 10,
        "plan_type": "credit_pack",
    },
    {
        "plan_id": 5,
        "name": "Credit Pack Medium",
        "description": "50 one-time credits.",
        "amount_cents": 2999,  # $29.99
        "currency": "usd",
        "recurring": None,
        "credits_granted": 50,
        "plan_type": "credit_pack",
    },
    {
        "plan_id": 6,
        "name": "Credit Pack Large",
        "description": "200 one-time credits.",
        "amount_cents": 7999,  # $79.99
        "currency": "usd",
        "recurring": None,
        "credits_granted": 200,
        "plan_type": "credit_pack",
    },
]


def find_existing_product(plan_id: int):
    """Return the first Stripe Product whose metadata.goc_plan_id == plan_id, or None."""
    # The Products list endpoint doesn't filter by metadata server-side,
    # so we paginate locally. With ~5 products this is trivially fast.
    for product in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if product.metadata.get("goc_plan_id") == str(plan_id):
            return product
    return None


def find_existing_price(product_id: str, plan_id: int):
    """Return the first active Price for `product_id` tagged with our plan_id metadata."""
    for price in stripe.Price.list(product=product_id, active=True, limit=100).auto_paging_iter():
        if price.metadata.get("goc_plan_id") == str(plan_id):
            return price
    # Fallback: any active price on the product (some users may have created
    # the Price manually in the Dashboard without metadata).
    prices = list(stripe.Price.list(product=product_id, active=True, limit=1).auto_paging_iter())
    return prices[0] if prices else None


def ensure_product_and_price(spec: dict) -> tuple[str, str]:
    """Idempotently create / fetch the Product+Price for one plan.

    Returns (product_id, price_id).
    """
    plan_id = spec["plan_id"]

    product = find_existing_product(plan_id)
    if product is None:
        product = stripe.Product.create(
            name=spec["name"],
            description=spec["description"],
            metadata={
                "goc_plan_id": str(plan_id),
                "goc_plan_type": spec["plan_type"],
                "goc_credits_granted": str(spec["credits_granted"]),
            },
        )
        print(f"  [+] Created Product {product.id} ({spec['name']})")
    else:
        print(f"  [=] Reusing Product {product.id} ({spec['name']})")

    price = find_existing_price(product.id, plan_id)
    if price is None:
        price_kwargs = dict(
            product=product.id,
            unit_amount=spec["amount_cents"],
            currency=spec["currency"],
            metadata={
                "goc_plan_id": str(plan_id),
                "goc_credits_granted": str(spec["credits_granted"]),
            },
        )
        if spec["recurring"]:
            price_kwargs["recurring"] = spec["recurring"]
        price = stripe.Price.create(**price_kwargs)
        print(f"  [+] Created Price   {price.id} ({spec['amount_cents']/100:.2f} {spec['currency'].upper()})")
    else:
        print(f"  [=] Reusing Price   {price.id} ({price.unit_amount/100:.2f} {price.currency.upper()})")

    return product.id, price.id


def main():
    if not stripe.api_key:
        print("ERROR: STRIPE_SECRET_KEY is empty. Set it in .env or env vars.", file=sys.stderr)
        sys.exit(1)

    print(f"Stripe API key prefix: {stripe.api_key[:8]}...   api_version={stripe.api_version}")
    print(f"Bootstrapping {len(PRODUCTS)} paid plans...\n")

    mapping: list[tuple[int, str, str, str]] = []
    for spec in PRODUCTS:
        print(f"-> plan_id={spec['plan_id']}  {spec['name']}")
        product_id, price_id = ensure_product_and_price(spec)
        mapping.append((spec["plan_id"], spec["name"], product_id, price_id))
        print()

    print("=" * 80)
    print("Paste these into scripts/seed_data.py (`stripe_price_id` per plan):")
    print("=" * 80)
    print(f"{'plan_id':<8}  {'name':<22}  {'stripe_product_id':<28}  {'stripe_price_id'}")
    for plan_id, name, product_id, price_id in mapping:
        print(f"{plan_id:<8}  {name:<22}  {product_id:<28}  {price_id}")
    print("=" * 80)


if __name__ == "__main__":
    main()
