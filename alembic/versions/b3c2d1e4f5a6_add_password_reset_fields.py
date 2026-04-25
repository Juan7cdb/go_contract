"""Add password reset fields to users

Revision ID: b3c2d1e4f5a6
Revises: a6b66a5e153a
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c2d1e4f5a6'
down_revision: Union[str, None] = 'a6b66a5e153a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expiry', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_token_expiry')
    op.drop_column('users', 'reset_token')
