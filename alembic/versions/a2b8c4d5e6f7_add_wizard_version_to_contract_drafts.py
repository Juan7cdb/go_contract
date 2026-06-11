"""Add wizard_version to contract_drafts

Revision ID: a2b8c4d5e6f7
Revises: f1a7c9d2e8b4
Create Date: 2026-06-11 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a2b8c4d5e6f7'
down_revision: Union[str, None] = 'f1a7c9d2e8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'contract_drafts',
        sa.Column('wizard_version', sa.Integer(), server_default='1', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('contract_drafts', 'wizard_version')
