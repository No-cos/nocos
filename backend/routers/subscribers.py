# routers/subscribers.py
# REST API endpoint for email newsletter subscriptions.
# Handles new subscriptions and email confirmation.
# Email addresses are never returned in API responses or logged in full.

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.subscriber import Subscriber
from schemas.subscriber import SubscribeRequest, SubscribeResponse
from services.email import send_confirmation_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscribe", tags=["subscribers"])


@router.post("", response_model=SubscribeResponse)
def subscribe(body: SubscribeRequest, db: Session = Depends(get_db)) -> dict:
    """
    Subscribe an email address to the Nocos weekly digest.

    Behaviour:
    - If the email is new: creates a Subscriber record, sends confirmation email
    - If the email already exists and is confirmed: returns success silently
    - If the email exists but unconfirmed: resends the confirmation email
    - If the email is unsubscribed: reactivates the subscription

    Returns success=True in all cases — this prevents enumeration of which
    emails are already registered (SKILLS.md Section 16).

    Args:
        body: Validated SubscribeRequest with email and optional tag_preferences

    Returns:
        SubscribeResponse: { success: True, message: str }
    """
    # Check for existing subscriber — email is unique-constrained in the DB
    existing = db.query(Subscriber).filter(Subscriber.email == body.email).first()

    if existing:
        if existing.unsubscribed_at is not None:
            # Reactivate — clear the unsubscribed_at timestamp
            existing.unsubscribed_at = None
            existing.confirmed = False
            existing.tag_preferences = body.tag_preferences
            db.add(existing)
            db.commit()
            send_confirmation_email(body.email, str(existing.id))

        elif not existing.confirmed:
            # Resend confirmation for unconfirmed subscribers
            send_confirmation_email(body.email, str(existing.id))

        # Return the same message regardless of the existing state —
        # prevents email enumeration
        return SubscribeResponse(message="Check your inbox for a confirmation email.")

    # New subscriber
    subscriber = Subscriber(
        email=body.email,
        tag_preferences=body.tag_preferences,
        confirmed=False,
    )
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)

    # Send confirmation email — failure does not block the API response.
    # The subscriber record is created regardless; they can re-submit to resend.
    send_confirmation_email(body.email, str(subscriber.id))

    logger.info(
        "New subscriber created",
        extra={"subscriber_id": str(subscriber.id)},
        # Note: email address is intentionally not logged (SKILLS.md §12)
    )

    return SubscribeResponse(message="Check your inbox for a confirmation email.")


@router.get("/confirm/{subscriber_id}")
def confirm_subscription(subscriber_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Confirm a subscription via the token sent in the confirmation email.

    The subscriber_id from the email link is used as the confirmation token.
    Sets confirmed=True so the subscriber will receive weekly digests.

    Args:
        subscriber_id: UUID from the confirmation email link

    Returns:
        { success: True, message: str }

    Raises:
        404 if the subscriber ID is not found
    """
    try:
        uid = UUID(subscriber_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid confirmation link")

    subscriber = db.query(Subscriber).filter(Subscriber.id == uid).first()

    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Confirmation link not found", "code": "INVALID_TOKEN"},
        )

    if subscriber.confirmed:
        # Already confirmed — idempotent, return success
        return {"success": True, "message": "Your subscription is already confirmed."}

    from datetime import datetime, timezone
    subscriber.confirmed = True
    subscriber.confirmed_at = datetime.now(tz=timezone.utc)
    db.add(subscriber)
    db.commit()

    logger.info(
        "Subscription confirmed",
        extra={"subscriber_id": str(subscriber.id)},
    )

    return {"success": True, "message": "You're confirmed. Your first digest will arrive soon."}
