# models/subscriber.py
# SQLAlchemy model for a Nocos email subscriber.
# Subscribers receive a weekly digest of curated non-code issues
# filtered by their tag preferences (e.g. design, documentation).

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from models.base import Base


class Subscriber(Base):
    """
    Represents a person subscribed to the Nocos weekly digest.

    Double opt-in is enforced: a subscriber is only active after they
    click the confirmation link in the email (confirmed=True). Unconfirmed
    subscribers are never included in digest sends.

    Unsubscribes are soft — unsubscribed_at is set rather than deleting the
    row, so we never accidentally re-subscribe someone.

    tag_preferences is nullable — a null value means "send me everything".
    """

    __tablename__ = "subscribers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Unique constraint prevents duplicate subscriptions.
    # The API returns success even for duplicate emails to avoid enumeration.
    email = Column(String(320), nullable=False, unique=True)

    # Which contribution types this subscriber wants in their digest.
    # Null means all types. Stored as a string array matching contribution_type_enum.
    tag_preferences = Column(ARRAY(String), nullable=True)

    # False until the subscriber clicks the confirmation link in their welcome email.
    # Only confirmed subscribers receive weekly digests.
    confirmed = Column(Boolean, nullable=False, default=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    subscribed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Set when the user unsubscribes. We never delete subscriber rows.
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        # Mask the email in repr so it doesn't leak into logs accidentally
        masked = self.email[:2] + "***" if self.email else "unknown"
        return f"<Subscriber {masked}>"
