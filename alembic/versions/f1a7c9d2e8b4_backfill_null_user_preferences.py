"""backfill_null_user_preferences

Even though `users.preferences` is declared `NOT NULL DEFAULT '{}'` in the
schema (see `631a19033106_add_user_preferences.py`), legacy rows inserted
through paths that bypassed the default — or restored from older dumps —
may still hold NULL. The application code defends against this with an
`or {}` fallback at every read site, but normalising the column shape
keeps reporting / downstream consumers honest.

This migration is idempotent: re-running it is a no-op once every row has
a JSON value. Downgrade intentionally does nothing; we never want to
recreate NULLs.

Revision ID: f1a7c9d2e8b4
Revises: e9f6a4b2c1d3
Create Date: 2026-06-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1a7c9d2e8b4'
down_revision: Union[str, None] = 'e9f6a4b2c1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # JSON column → cast literal to jsonb for safety with both `JSON` and
    # `JSONB` column types. Postgres will accept jsonb being implicitly
    # converted back into the declared column type.
    op.execute(
        "UPDATE users SET preferences = '{}'::jsonb WHERE preferences IS NULL"
    )


def downgrade() -> None:
    # No-op: we don't want to undo a data-normalisation backfill.
    pass
