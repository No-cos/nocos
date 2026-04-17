# models/program.py
# SQLAlchemy model for the programs table.
# Programs are structured stipend programs (GSoC, Outreachy, LFX, etc.) —
# curated by admins, not scraped. They have defined application windows
# and deadlines, and are displayed on the /programs page.

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from models.base import Base


class Program(Base):
    """
    Represents a paid stipend program listed on Nocos.

    Programs are manually curated — never scraped. Status values:
      upcoming — application window has not opened yet
      open     — accepting applications right now
      closed   — application deadline has passed (kept visible, greyed out)

    Closed programs remain visible so contributors can plan for future cohorts.
    """

    __tablename__ = "programs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Human-readable program name (e.g. "Google Summer of Code 2026")
    name = Column(String(255), nullable=False)

    # Organising body (e.g. "Google", "Linux Foundation")
    organisation = Column(String(255), nullable=False)

    # URL to the organisation logo image — nullable, card shows initials as fallback
    logo_url = Column(String(2048), nullable=True)

    # Plain-text description shown on the card and detail view
    description = Column(Text, nullable=False)

    # Human-readable stipend range (e.g. "$1,500 – $6,600")
    stipend_range = Column(String(100), nullable=False)

    # Application window — both are nullable for rolling/TBD programs
    application_open = Column(Date, nullable=True)
    application_deadline = Column(Date, nullable=True)

    # When the program period itself starts (not the application deadline)
    program_start = Column(Date, nullable=True)

    # Freeform tags stored as a JSON array of strings
    # e.g. ["documentation", "design", "ai", "open-source"]
    tags = Column(JSON, nullable=False, default=list)

    # Direct link to the application or program homepage
    application_url = Column(String(2048), nullable=False)

    # Explicit status — admin can override; seed script sets initial values
    status = Column(
        Enum("upcoming", "open", "closed", name="program_status_enum"),
        nullable=False,
        default="upcoming",
        index=True,
    )

    # False hides the program from all public responses without deleting it
    is_active = Column(Boolean, nullable=False, default=True, index=True)

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

    def __repr__(self) -> str:
        return f"<Program {self.name!r} status={self.status!r}>"
