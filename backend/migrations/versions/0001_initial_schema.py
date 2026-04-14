"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-14

Creates all initial tables:
  - projects
  - tasks
  - subscribers
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums — DO block catches duplicate_object so re-runs are safe ──────────
    conn = op.get_bind()
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

    # Reference enums for column definitions
    activity_status_enum = sa.Enum(
        "active", "slow", "inactive", name="activity_status_enum", create_type=False
    )
    contribution_type_enum = sa.Enum(
        "design", "documentation", "translation", "research", "pr_review",
        "data_analytics", "community", "marketing", "social_media",
        "project_management", "other",
        name="contribution_type_enum", create_type=False,
    )
    difficulty_enum = sa.Enum(
        "beginner", "intermediate", "advanced", name="difficulty_enum", create_type=False
    )
    task_source_enum = sa.Enum(
        "github_scrape", "manual_post", name="task_source_enum", create_type=False
    )
    hidden_reason_enum = sa.Enum(
        "closed", "stale", "archived", name="hidden_reason_enum", create_type=False
    )

    # ── projects ───────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("github_url", sa.String(512), nullable=False, unique=True),
        sa.Column("github_owner", sa.String(255), nullable=False),
        sa.Column("github_repo", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("website_url", sa.String(512), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=False),
        sa.Column(
            "social_links",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("activity_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "activity_status",
            activity_status_enum,
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_commit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_projects_github_owner", "projects", ["github_owner"])

    # ── tasks ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("github_issue_id", sa.Integer, nullable=True, unique=True),
        sa.Column("github_issue_number", sa.Integer, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description_original", sa.Text, nullable=True),
        sa.Column("description_display", sa.Text, nullable=False),
        sa.Column("is_ai_generated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "labels",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "contribution_type",
            contribution_type_enum,
            nullable=False,
            server_default="other",
        ),
        sa.Column("is_paid", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("difficulty", difficulty_enum, nullable=True),
        sa.Column(
            "source",
            task_source_enum,
            nullable=False,
            server_default="github_scrape",
        ),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_issue_url", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("hidden_reason", hidden_reason_enum, nullable=True),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_contribution_type", "tasks", ["contribution_type"])
    op.create_index("ix_tasks_github_created_at", "tasks", ["github_created_at"])
    op.create_index("ix_tasks_is_active", "tasks", ["is_active"])

    # ── subscribers ────────────────────────────────────────────────────────────
    op.create_table(
        "subscribers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("tag_preferences", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "subscribed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("subscribers")
    op.drop_index("ix_tasks_is_active", table_name="tasks")
    op.drop_index("ix_tasks_github_created_at", table_name="tasks")
    op.drop_index("ix_tasks_contribution_type", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_projects_github_owner", table_name="projects")
    op.drop_table("projects")

    sa.Enum(name="hidden_reason_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_source_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="difficulty_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="contribution_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="activity_status_enum").drop(op.get_bind(), checkfirst=True)
