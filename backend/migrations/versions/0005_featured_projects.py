"""create featured_projects table

Revision ID: 0005_featured_projects
Revises: 0004_add_task_submitter_email
Create Date: 2026-04-17

Creates the featured_projects table used by the /api/v1/featured endpoint.
Each row represents a single repo in a weekly snapshot; two categories
are stored (most_active, new_promising) — up to 6 rows per category per week.

The weekly_featured_refresh APScheduler job populates this table every
Sunday at 00:00 UTC (services/sync.py).

Idempotent: the CREATE TABLE and CREATE TYPE statements are wrapped in
DO blocks that swallow "already exists" errors so the migration is safe
to run multiple times.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0005_featured_projects"
down_revision = "0004_add_task_submitter_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create the ENUM type first — idempotent
    conn.execute(sa.text("""
        DO $$
        BEGIN
            CREATE TYPE featured_category AS ENUM ('most_active', 'new_promising');
        EXCEPTION
            WHEN duplicate_object THEN
                NULL;  -- type already exists, nothing to do
        END $$;
    """))

    # Create the table — idempotent
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS featured_projects (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            repo_full_name  VARCHAR(255) NOT NULL,
            name            VARCHAR(255) NOT NULL,
            description     TEXT        NOT NULL DEFAULT '',
            language        VARCHAR(100),
            stars           INTEGER     NOT NULL DEFAULT 0,
            stars_gained_this_week INTEGER,
            forks           INTEGER     NOT NULL DEFAULT 0,
            open_issues_count INTEGER   NOT NULL DEFAULT 0,
            homepage        VARCHAR(2048),
            license         VARCHAR(100),
            topics          JSONB       NOT NULL DEFAULT '[]',
            weekly_commits  INTEGER     NOT NULL DEFAULT 0,
            avatar_url      VARCHAR(2048) NOT NULL DEFAULT '',
            github_url      VARCHAR(2048) NOT NULL DEFAULT '',
            category        featured_category NOT NULL,
            week_of         DATE        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))

    # Index on (category, week_of) — the /featured endpoint always filters by both
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_featured_projects_category_week
        ON featured_projects (category, week_of);
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS featured_projects;"))
    conn.execute(sa.text("DROP TYPE IF EXISTS featured_category;"))
