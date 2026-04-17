"""add programs table

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-17

Fully idempotent — mirrors the pattern used in 0001 and 0005:
  - conn.execute(sa.text(...)) with raw SQL throughout
  - DO $$ BEGIN ... EXCEPTION WHEN duplicate_object ... END $$; for enum creation
  - CREATE TABLE IF NOT EXISTS so a partial previous run never blocks a retry
  - CREATE INDEX IF NOT EXISTS for the same reason

This avoids op.create_table() entirely, which was emitting a bare
CREATE TYPE regardless of create_type=False and causing a
DuplicateObject error on re-run after a partial deployment.
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create the ENUM type — idempotent
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE program_status_enum AS ENUM ('upcoming', 'open', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create the table — idempotent
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS programs (
            id                   UUID            NOT NULL PRIMARY KEY,
            name                 VARCHAR(255)    NOT NULL,
            organisation         VARCHAR(255)    NOT NULL,
            logo_url             VARCHAR(2048),
            description          TEXT            NOT NULL,
            stipend_range        VARCHAR(100)    NOT NULL,
            application_open     DATE,
            application_deadline DATE,
            program_start        DATE,
            tags                 JSON            NOT NULL DEFAULT '[]',
            application_url      VARCHAR(2048)   NOT NULL,
            status               program_status_enum NOT NULL DEFAULT 'upcoming',
            is_active            BOOLEAN         NOT NULL DEFAULT TRUE,
            created_at           TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ     NOT NULL DEFAULT now()
        );
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_programs_status
            ON programs (status);
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_programs_is_active
            ON programs (is_active);
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_programs_is_active;"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_programs_status;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS programs;"))
    conn.execute(sa.text("DROP TYPE IF EXISTS program_status_enum;"))
