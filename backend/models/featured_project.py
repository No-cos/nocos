# models/featured_project.py
# ORM model for the featured_projects table.
# Each row represents one project in a weekly "featured" snapshot.
# Two categories are tracked per week:
#   most_active     — repos with the highest commit/issue activity over 7 days
#   new_promising   — repos created in the last 90 days with strong star momentum
#
# The table is populated (or refreshed) every Sunday at 00:00 UTC by the
# weekly_featured_refresh scheduler job in services/sync.py.
# The /api/v1/featured endpoint reads from this table directly.

import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from models.base import Base


class FeaturedProject(Base):
    __tablename__ = "featured_projects"

    # Primary key — random UUID so rows are not guessable
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # "owner/repo" full name — combined with week_of for uniqueness
    repo_full_name = Column(String(255), nullable=False, index=True)

    # Human-readable display name (may differ from repo slug)
    name = Column(String(255), nullable=False)

    # Repo description from GitHub (may be empty string, never NULL)
    description = Column(Text, nullable=False, default="")

    # Primary programming language reported by GitHub
    language = Column(String(100), nullable=True)

    # Total star count at the time of snapshot
    stars = Column(Integer, nullable=False, default=0)

    # Stars gained in the 7 days ending on week_of (null for most_active)
    stars_gained_this_week = Column(Integer, nullable=True)

    # Fork count at the time of snapshot
    forks = Column(Integer, nullable=False, default=0)

    # Open issue count at the time of snapshot
    open_issues_count = Column(Integer, nullable=False, default=0)

    # Project homepage URL (may be null)
    homepage = Column(String(2048), nullable=True)

    # SPDX license identifier (e.g. "MIT", "Apache-2.0")
    license = Column(String(100), nullable=True)

    # GitHub topics list stored as a JSON array of strings
    topics = Column(JSON, nullable=False, default=list)

    # Sum of commits across all branches in the last week (GitHub stat)
    weekly_commits = Column(Integer, nullable=False, default=0)

    # Avatar / owner profile image URL
    avatar_url = Column(String(2048), nullable=False, default="")

    # GitHub HTML URL for the repo (e.g. https://github.com/owner/repo)
    github_url = Column(String(2048), nullable=False, default="")

    # Which slot this project occupies in the featured section
    category = Column(
        Enum("most_active", "new_promising", name="featured_category"),
        nullable=False,
        index=True,
    )

    # The Monday of the ISO week this snapshot belongs to
    week_of = Column(Date, nullable=False, index=True)

    # Row creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<FeaturedProject {self.repo_full_name!r} "
            f"category={self.category!r} week={self.week_of}>"
        )
