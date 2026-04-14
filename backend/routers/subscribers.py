# routers/subscribers.py
# API endpoint for email newsletter subscriptions.
# Phase 1: Stub response. Full implementation in Phase 3.
# TODO: Validate email, store subscriber, send confirmation — see Phase 3

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import List, Optional

router = APIRouter(prefix="/subscribe", tags=["subscribers"])


class SubscribeRequest(BaseModel):
    """Request body for the subscribe endpoint."""
    email: EmailStr
    tag_preferences: Optional[List[str]] = None


@router.post("")
async def subscribe(body: SubscribeRequest) -> dict:
    """
    Subscribe an email address to the Nocos weekly digest.

    Validates the email, stores the subscriber with their tag preferences,
    and sends a confirmation email. Returns success even if the email is
    already subscribed — this prevents enumeration of subscriber emails.
    Full implementation in Phase 3.
    """
    # Phase 1 stub — full implementation in Phase 3
    return {
        "success": False,
        "error": "Not implemented yet",
        "code": "NOT_IMPLEMENTED",
    }
