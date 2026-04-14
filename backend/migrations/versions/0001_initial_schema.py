"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-14

Creates all initial tables:
  - projects
  - tasks
  - subscribers

This migration is fully idempotent:
  - Enums are created inside DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    so re-runs after a partial failure never crash on an already-existing enum type.
  - Tables are created with CREATE TABLE IF NOT EXISTS so re-runs after a partial
    failure never crash on an already-existing table.
  - Indexes are created with CREATE INDEX IF NOT EXISTS for the same reason.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Enums ──────────────────────────────────────────────────────────────────
    # Each CREATE TYPE is wrapped in a DO block so that if the type already
    # exists (e.g. from a previous failed run that created types but not tables)
    # the exception is silently swallowed and execution continues.

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE activity_status_enum AS ENUM ('active', 'slow', 'inactive');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE contribution_type_enum AS ENUM (
                'design', 'documentation', 'translation', 'research', 'pr_review',
                'data_analytics', 'community', 'marketing', 'social_media',
                'project_management', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE difficulty_enum AS ENUM ('beginner', 'intermediate', 'advanced');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE task_source_enum AS ENUM ('github_scrape', 'manual_post');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE hidden_reason_enum AS ENUM ('closed', 'stale', 'archived');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    # ── projects ───────────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS projects (
            id              UUID                        NOT NULL PRIMARY KEY,
            name            VARCHAR(255)                NOT NULL,
            github_url      VARCHAR(512)                NOT NULL UNIQUE,
            github_owner    VARCHAR(255)                NOT NULL,
            github_repo     VARCHAR(255)                NOT NULL,
            description     TEXT,
            website_url     VARCHAR(512),
            avatar_url      VARCHAR(512)                NOT NULL,
            social_links    JSON                        NOT NULL DEFAULT '{}',
            activity_score  INTEGER                     NOT NULL DEFAULT 0,
            activity_status activity_status_enum        NOT NULL DEFAULT 'active',
            last_commit_date TIMESTAMPTZ,
            is_active       BOOLEAN                     NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ                 NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ                 NOT NULL DEFAULT now()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_projects_github_owner
            ON projects (github_owner)
    """))

    # ── tasks ──────────────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS tasks (
            id                    UUID                     NOT NULL PRIMARY KEY,
            project_id            UUID                     NOT NULL
                                      REFERENCES projects (id) ON DELETE CASCADE,
            github_issue_id       INTEGER UNIQUE,
            github_issue_number   INTEGER,
            title                 VARCHAR(500)             NOT NULL,
            description_original  TEXT,
            description_display   TEXT                     NOT NULL,
            is_ai_generated       BOOLEAN                  NOT NULL DEFAULT FALSE,
            labels                TEXT[]                   NOT NULL DEFAULT '{}',
            contribution_type     contribution_type_enum   NOT NULL DEFAULT 'other',
            is_paid               BOOLEAN                  NOT NULL DEFAULT FALSE,
            difficulty            difficulty_enum,
            source                task_source_enum         NOT NULL DEFAULT 'github_scrape',
            github_created_at     TIMESTAMPTZ,
            github_issue_url      VARCHAR(512)             NOT NULL,
            is_active             BOOLEAN                  NOT NULL DEFAULT TRUE,
            hidden_reason         hidden_reason_enum,
            hidden_at             TIMESTAMPTZ,
            created_at            TIMESTAMPTZ              NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ              NOT NULL DEFAULT now()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tasks_project_id
            ON tasks (project_id)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tasks_contribution_type
            ON tasks (contribution_type)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tasks_github_created_at
            ON tasks (github_created_at)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tasks_is_active
            ON tasks (is_active)
    """))

    # ── subscribers ────────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id               UUID        NOT NULL PRIMARY KEY,
            email            VARCHAR(320) NOT NULL UNIQUE,
            tag_preferences  TEXT[],
            confirmed        BOOLEAN     NOT NULL DEFAULT FALSE,
            confirmed_at     TIMESTAMPTZ,
            subscribed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            unsubscribed_at  TIMESTAMPTZ
        )
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP TABLE IF EXISTS subscribers"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_is_active"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_github_created_at"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_contribution_type"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_project_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS tasks"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_projects_github_owner"))
    conn.execute(sa.text("DROP TABLE IF EXISTS projects"))

    conn.execute(sa.text("DROP TYPE IF EXISTS hidden_reason_enum"))
    conn.execute(sa.text("DROP TYPE IF EXISTS task_source_enum"))
    conn.execute(sa.text("DROP TYPE IF EXISTS difficulty_enum"))
    conn.execute(sa.text("DROP TYPE IF EXISTS contribution_type_enum"))
    conn.execute(sa.text("DROP TYPE IF EXISTS activity_status_enum"))
