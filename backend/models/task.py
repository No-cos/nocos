# models/task.py
# SQLAlchemy model for a non-code task (issue) displayed on Nocos.
# Tasks come from two sources:
#   1. github_scrape — pulled automatically from GitHub by the sync job
#   2. manual_post   — submitted directly by a maintainer via /post

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Task(Base):
    """
    Represents a single non-code task (issue) on the Nocos platform.

    Two description fields exist side-by-side:
      - description_original: the raw GitHub issue body (preserved for audit)
      - description_display:  what contributors see — either the original
                              (if it's good enough) or an AI-generated version

    Hidden tasks (is_active=False) are never shown on the platform but are
    kept in the database. hidden_reason records why a task was hidden so we
    can audit the sync logic.
    """

    __tablename__ = "tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Null for manually posted tasks — only scraped tasks have a GitHub issue ID
    github_issue_id = Column(BigInteger, nullable=True, unique=True)
    github_issue_number = Column(Integer, nullable=True)

    # Original GitHub issue title — preserved for audit; never altered.
    title = Column(String(500), nullable=False)

    # AI-rewritten title in plain, action-oriented language for non-technical
    # contributors. Null when generation has not yet run or failed. The API
    # returns this in preference to title; UI falls back to title when null.
    ai_title = Column(Text, nullable=True)

    # The original GitHub issue body — kept even if we replaced it with AI text.
    # Never exposed publicly via the API (SKILLS.md Section 16).
    description_original = Column(Text, nullable=True)

    # What contributors actually read. Either the original body (if >= 20 words)
    # or an AI-generated plain-English description.
    description_display = Column(Text, nullable=False)

    # True when Claude wrote description_display — shown as ✨ on the UI
    is_ai_generated = Column(Boolean, nullable=False, default=False)

    # Raw GitHub label names stored as an array for fast filtering
    labels = Column(ARRAY(String), nullable=False, default=list)

    contribution_type = Column(
        Enum(
            "design",
            "documentation",
            "translation",
            "research",
            "pr_review",
            "data_analytics",
            "community",
            "marketing",
            "social_media",
            "project_management",
            "other",
            name="contribution_type_enum",
        ),
        nullable=False,
        default="other",
        index=True,  # Indexed — filter by type is the most common query
    )

    is_paid = Column(Boolean, nullable=False, default=False)

    # Bounty fields — set by the scraper when it detects a real-money reward.
    # bounty_amount is stored in USD cents (integer) for precision.
    # Both default to False/None so existing rows are unaffected.
    is_bounty = Column(Boolean, nullable=False, default=False)
    bounty_amount = Column(Integer, nullable=True)  # USD cents, e.g. 5000 = $50

    difficulty = Column(
        Enum("beginner", "intermediate", "advanced", name="difficulty_enum"),
        nullable=True,
    )

    source = Column(
        Enum("github_scrape", "manual_post", "ai_generated", name="task_source_enum"),
        nullable=False,
        default="github_scrape",
    )

    # Null for manually posted tasks
    github_created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    github_issue_url = Column(String(512), nullable=False)

    # False when the task is stale, closed, or archived — never deleted
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Content moderation state for user-submitted tasks.
    # Scraped tasks are always 'approved'; manual_post tasks start as
    # 'pending_review' and only become visible once an admin approves them.
    # Valid values: approved | pending_review | rejected
    review_status = Column(String(20), nullable=False, default="approved", index=True)

    # Contact email provided by the submitter on the Post a Task form.
    # Only stored for manual_post tasks. Never returned in any public API response.
    submitter_email = Column(String(254), nullable=True)

    hidden_reason = Column(
        Enum("closed", "stale", "archived", name="hidden_reason_enum"),
        nullable=True,
    )
    hidden_at = Column(DateTime(timezone=True), nullable=True)

    # When this task was first added to Nocos (not the GitHub created date)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship — each task belongs to one project
    project = relationship("Project", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task {self.id} — {self.title[:40]}>"
