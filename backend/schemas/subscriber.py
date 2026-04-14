# schemas/subscriber.py
# Pydantic schemas for the Subscriber model.
# Email addresses are never returned in API responses — only used internally.

from typing import List, Optional

from pydantic import BaseModel, EmailStr


class SubscribeRequest(BaseModel):
    """Request body for POST /api/v1/subscribe."""
    email: EmailStr
    tag_preferences: Optional[List[str]] = None


class SubscribeResponse(BaseModel):
    """
    Response after a successful subscription request.

    Returns success=True even if the email is already subscribed.
    This prevents an attacker from enumerating which emails are registered.
    """
    success: bool = True
    message: str = "Check your inbox for a confirmation email."
