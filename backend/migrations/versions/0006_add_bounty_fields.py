"""add bounty fields to tasks

Revision ID: 0006
Revises: 0005_featured_projects
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005_featured_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # is_bounty: False for all existing rows (safe default — nothing was a bounty before)
    op.add_column(
        "tasks",
        sa.Column("is_bounty", sa.Boolean(), nullable=False, server_default="false"),
    )
    # bounty_amount: nullable — most tasks have no bounty
    op.add_column(
        "tasks",
        sa.Column("bounty_amount", sa.Integer(), nullable=True),
    )
    # Index on is_bounty to make the bounty filter fast
    op.create_index("ix_tasks_is_bounty", "tasks", ["is_bounty"])


def downgrade() -> None:
    op.drop_index("ix_tasks_is_bounty", table_name="tasks")
    op.drop_column("tasks", "bounty_amount")
    op.drop_column("tasks", "is_bounty")
