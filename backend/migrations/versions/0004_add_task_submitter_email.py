"""add submitter_email to tasks

Revision ID: 0004_add_task_submitter_email
Revises: 0003_add_task_review_status
Create Date: 2026-04-16

Adds a submitter_email column to store the contact address provided by the
maintainer when posting a task via the /post form. The column is:

  - nullable (scraped tasks never have a submitter email)
  - only returned by the protected admin /pending endpoint
  - intentionally absent from all public API responses

Idempotent: wraps the ALTER TABLE in a DO block that swallows
duplicate_column so re-running never crashes.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0004_add_task_submitter_email"
down_revision = "0003_add_task_review_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotent column addition — no-op if column already exists
    conn.execute(sa.text("""
        DO $$
        BEGIN
            ALTER TABLE tasks
                ADD COLUMN submitter_email VARCHAR(254);
        EXCEPTION
            WHEN duplicate_column THEN
                NULL;  -- column already exists, nothing to do
        END $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS submitter_email;"))
