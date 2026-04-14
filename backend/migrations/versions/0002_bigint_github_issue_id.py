"""bigint github_issue_id

Revision ID: 0002_bigint_github_issue_id
Revises: 0001_initial_schema
Create Date: 2026-04-15

GitHub issue IDs have grown beyond 2^31 (~2.1 billion), exceeding the
PostgreSQL INTEGER range. Widen github_issue_id to BIGINT so large IDs
(e.g. 4249778080) can be stored without a NumericValueOutOfRange error.

Idempotent: uses ALTER COLUMN ... TYPE which is safe to re-run if the
column is already BIGINT (PostgreSQL is a no-op in that case).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0002_bigint_github_issue_id"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE tasks
        ALTER COLUMN github_issue_id TYPE BIGINT
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE tasks
        ALTER COLUMN github_issue_id TYPE INTEGER
    """))
