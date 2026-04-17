"""add programs table

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the program_status_enum type first
    program_status_enum = sa.Enum(
        "upcoming", "open", "closed", name="program_status_enum"
    )
    program_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "programs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("organisation", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("stipend_range", sa.String(100), nullable=False),
        sa.Column("application_open", sa.Date(), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("program_start", sa.Date(), nullable=True),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("application_url", sa.String(2048), nullable=False),
        sa.Column(
            "status",
            sa.Enum("upcoming", "open", "closed", name="program_status_enum"),
            nullable=False,
            server_default="upcoming",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_programs_status", "programs", ["status"])
    op.create_index("ix_programs_is_active", "programs", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_programs_is_active", table_name="programs")
    op.drop_index("ix_programs_status", table_name="programs")
    op.drop_table("programs")
    sa.Enum(name="program_status_enum").drop(op.get_bind(), checkfirst=True)
