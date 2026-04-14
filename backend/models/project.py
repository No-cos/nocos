# models/project.py
# SQLAlchemy model for an open source project tracked on Nocos.
# A project is the parent of many tasks (issues). Projects are populated
# either by the GitHub scraper or when a maintainer posts a task manually.

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class ActivityStatus(str):
    """Enum values for a project's commit activity status."""
    ACTIVE = "active"
    SLOW = "slow"
    INACTIVE = "inactive"


class Project(Base):
    """
    Represents an open source project listed on Nocos.

    Projects are the parent entity for tasks. Each project maps to a single
    GitHub repository. The activity_status is recalculated on every sync
    based on the last_commit_date:
      - active:   last commit within 30 days
      - slow:     last commit 30–90 days ago
      - inactive: last commit over 90 days ago

    Soft deletes are used — is_active is set to False rather than deleting
    the row. This preserves the audit trail and prevents broken task links.
    """

    __tablename__ = "projects"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    github_url = Column(String(512), nullable=False, unique=True)
    github_owner = Column(String(255), nullable=False, index=True)
    github_repo = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    website_url = Column(String(512), nullable=True)
    avatar_url = Column(String(512), nullable=False)

    # JSON blob storing optional social links for this project.
    # Only the github key is always present — others are null if not found.
    # Schema: { twitter, discord, slack, linkedin, youtube, github }
    social_links = Column(JSON, nullable=False, default=dict)

    # Activity score (0–100) is a computed field updated on each sync.
    # It's stored so we can sort by it without recalculating on every request.
    activity_score = Column(Integer, nullable=False, default=0)

    activity_status = Column(
        Enum("active", "slow", "inactive", name="activity_status_enum"),
        nullable=False,
        default="active",
    )
    last_commit_date = Column(DateTime(timezone=True), nullable=True)

    # Set to False when the GitHub repo is archived or deleted.
    # False projects and all their tasks are hidden from the platform.
    is_active = Column(Boolean, nullable=False, default=True)

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

    # Relationship — a project has many tasks
    tasks = relationship("Task", back_populates="project", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Project {self.github_owner}/{self.github_repo}>"
