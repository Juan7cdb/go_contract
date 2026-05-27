"""lower default credits to 0

Revision ID: d8e5f3a1b2c0
Revises: c7d4e1f2a3b8
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd8e5f3a1b2c0'
down_revision: Union[str, None] = 'c7d4e1f2a3b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'credits_remaining', server_default='0')


def downgrade() -> None:
    op.alter_column('users', 'credits_remaining', server_default='5')
