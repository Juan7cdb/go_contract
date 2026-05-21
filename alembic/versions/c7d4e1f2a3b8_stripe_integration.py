"""stripe_integration

Adds Stripe columns to users/plans/subscriptions and creates the new
`payments` and `stripe_events` tables. Source of truth: Phase 1 of
`thoughts/juandavid/plans/2026-05-20-stripe-monetization-plan.md`.

Revision ID: c7d4e1f2a3b8
Revises: b3c2d1e4f5a6
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c7d4e1f2a3b8'
down_revision: Union[str, None] = 'b3c2d1e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: add stripe_customer_id ----------------------------------
    op.add_column(
        'users',
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f('ix_users_stripe_customer_id'),
        'users',
        ['stripe_customer_id'],
        unique=True,
    )

    # --- plans: stripe price/product + plan_type + currency + is_active ---
    op.add_column(
        'plans',
        sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        'uq_plans_stripe_price_id', 'plans', ['stripe_price_id']
    )
    op.add_column(
        'plans',
        sa.Column('stripe_product_id', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'plans',
        sa.Column(
            'plan_type',
            sa.String(length=50),
            nullable=False,
            server_default='subscription',
        ),
    )
    op.add_column(
        'plans',
        sa.Column(
            'currency',
            sa.String(length=10),
            nullable=False,
            server_default='usd',
        ),
    )
    op.add_column(
        'plans',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )

    # --- subscriptions: stripe mirror columns ---------------------------
    op.add_column(
        'subscriptions',
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f('ix_subscriptions_stripe_subscription_id'),
        'subscriptions',
        ['stripe_subscription_id'],
        unique=True,
    )
    op.add_column(
        'subscriptions',
        sa.Column(
            'status',
            sa.String(length=50),
            nullable=False,
            server_default='active',
        ),
    )
    op.add_column(
        'subscriptions',
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'subscriptions',
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'subscriptions',
        sa.Column(
            'cancel_at_period_end',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'subscriptions',
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
    )

    # --- payments table -------------------------------------------------
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column(
            'currency',
            sa.String(length=10),
            nullable=False,
            server_default='usd',
        ),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column(
            'credits_granted',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
        sa.Column('payment_type', sa.String(length=50), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_payment_intent_id', name='uq_payments_payment_intent'),
        sa.UniqueConstraint('stripe_invoice_id', name='uq_payments_invoice'),
        sa.UniqueConstraint('stripe_checkout_session_id', name='uq_payments_session'),
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_user_id'), 'payments', ['user_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)

    # --- stripe_events table --------------------------------------------
    op.create_table(
        'stripe_events',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column(
            'processed_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_stripe_events_event_type'),
        'stripe_events',
        ['event_type'],
        unique=False,
    )


def downgrade() -> None:
    # --- stripe_events --------------------------------------------------
    op.drop_index(op.f('ix_stripe_events_event_type'), table_name='stripe_events')
    op.drop_table('stripe_events')

    # --- payments -------------------------------------------------------
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_user_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')

    # --- subscriptions --------------------------------------------------
    op.drop_column('subscriptions', 'canceled_at')
    op.drop_column('subscriptions', 'cancel_at_period_end')
    op.drop_column('subscriptions', 'current_period_end')
    op.drop_column('subscriptions', 'current_period_start')
    op.drop_column('subscriptions', 'status')
    op.drop_index(
        op.f('ix_subscriptions_stripe_subscription_id'),
        table_name='subscriptions',
    )
    op.drop_column('subscriptions', 'stripe_subscription_id')

    # --- plans ----------------------------------------------------------
    op.drop_column('plans', 'is_active')
    op.drop_column('plans', 'currency')
    op.drop_column('plans', 'plan_type')
    op.drop_column('plans', 'stripe_product_id')
    op.drop_constraint('uq_plans_stripe_price_id', 'plans', type_='unique')
    op.drop_column('plans', 'stripe_price_id')

    # --- users ----------------------------------------------------------
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')
    op.drop_column('users', 'stripe_customer_id')
