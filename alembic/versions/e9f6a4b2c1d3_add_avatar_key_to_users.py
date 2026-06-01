"""Add avatar_key to users

Revision ID: e9f6a4b2c1d3
Revises: d8e5f3a1b2c0
Create Date: 2026-06-01 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e9f6a4b2c1d3'
down_revision: Union[str, None] = 'd8e5f3a1b2c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_key', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_key')
