"""add ai_title column to tasks

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-20

Adds ai_title (nullable TEXT) to the tasks table.
This stores an AI-rewritten plain-English title for each issue so
non-technical contributors see an action-oriented headline instead of
the raw, often jargon-heavy GitHub issue title.

The column is nullable — generation happens asynchronously during the
scrape/backfill cycle. NULL means enrichment has not run yet.
Idempotent: uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_title TEXT;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE tasks DROP COLUMN IF EXISTS ai_title;
    """))
