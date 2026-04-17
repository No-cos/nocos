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
    # Create the enum type with an idempotent DO block so a partially-applied
    # migration (e.g. from a previous failed deploy that created the type but
    # not the table) doesn't raise "type already exists" on retry.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE program_status_enum AS ENUM ('upcoming', 'open', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # create_type=False on the Enum tells SQLAlchemy not to issue a second
    # CREATE TYPE inside create_table — we handle it ourselves above.
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
            sa.Enum("upcoming", "open", "closed", name="program_status_enum", create_type=False),
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
    op.execute("DROP TYPE IF EXISTS program_status_enum;")
