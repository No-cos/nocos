"""add task review_status column

Revision ID: 0003_add_task_review_status
Revises: 0002_bigint_github_issue_id
Create Date: 2026-04-16

Adds a review_status column to the tasks table to support content moderation
for user-submitted tasks. Valid values: approved, pending_review, rejected.

DEFAULT 'approved' ensures all existing scraped GitHub/GitLab issues remain
visible immediately — only new manual_post tasks will default to pending_review
(that default is set in application code, not here).

Idempotent: the column addition is wrapped in a DO block that silently swallows
the duplicate_column error if the column already exists, so re-running this
migration never crashes.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0003_add_task_review_status"
down_revision = "0002_bigint_github_issue_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotent column addition — no-op if already present
    conn.execute(sa.text("""
        DO $$
        BEGIN
            ALTER TABLE tasks
                ADD COLUMN review_status VARCHAR(20) NOT NULL DEFAULT 'approved';
        EXCEPTION
            WHEN duplicate_column THEN
                NULL;  -- column already exists, nothing to do
        END $$;
    """))

    # Index so pending task queries stay fast even with many rows
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tasks_review_status
            ON tasks (review_status);
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_review_status;"))
    conn.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS review_status;"))
