# tests/integration/test_subscribe_api.py
# Integration tests for POST /api/v1/subscribe.
#
# Key behavioural note from the router implementation:
#   - The endpoint ALWAYS returns success=True regardless of whether the email
#     already exists. This is intentional — it prevents email enumeration.
#   - There is therefore NO 409 path; a duplicate confirmed subscriber still
#     receives a 200 with success=True.
#
# The real database is replaced by a MagicMock session (see conftest.py).
# send_confirmation_email is patched so no real SMTP calls are made.

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ─── POST /api/v1/subscribe ───────────────────────────────────────────────────

def test_subscribe_creates_subscriber(client, mock_db_session):
    """
    A new email address results in a 200 response with success=True.

    The DB has no existing subscriber (first() returns None), so a new
    Subscriber record is created and a confirmation email is sent.
    """
    # No existing subscriber in the DB.
    mock_db_session._query_result = []

    with patch("routers.subscribers.send_confirmation_email", return_value=True):
        response = client.post(
            "/api/v1/subscribe",
            json={"email": "test@example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "message" in body


def test_subscribe_duplicate_confirmed_email_returns_success(client, mock_db_session):
    """
    Submitting an already-confirmed email still returns success=True.

    The router never raises a 409 — it intentionally hides whether an address
    is registered to prevent email enumeration (see router docstring).
    """
    existing = MagicMock()
    existing.id = uuid4()
    existing.confirmed = True
    existing.unsubscribed_at = None  # Not unsubscribed
    mock_db_session._query_result = [existing]

    with patch("routers.subscribers.send_confirmation_email", return_value=True):
        response = client.post(
            "/api/v1/subscribe",
            json={"email": "already@example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_subscribe_invalid_email_returns_422(client, mock_db_session):
    """A request body with an invalid email address is rejected with 422."""
    response = client.post(
        "/api/v1/subscribe",
        json={"email": "not-an-email"},
    )

    assert response.status_code == 422


def test_subscribe_unconfirmed_duplicate_resends_email(client, mock_db_session):
    """
    An existing but unconfirmed subscriber receives a resent confirmation
    email. The response is still 200 with success=True.
    """
    existing = MagicMock()
    existing.id = uuid4()
    existing.confirmed = False
    existing.unsubscribed_at = None
    mock_db_session._query_result = [existing]

    with patch("routers.subscribers.send_confirmation_email", return_value=True) as mock_email:
        response = client.post(
            "/api/v1/subscribe",
            json={"email": "unconfirmed@example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    # Confirmation email should have been resent once.
    mock_email.assert_called_once()


def test_subscribe_reactivates_unsubscribed_email(client, mock_db_session):
    """
    A previously unsubscribed email is reactivated and a confirmation email
    is sent. The response is 200 with success=True.
    """
    from datetime import datetime, timezone

    existing = MagicMock()
    existing.id = uuid4()
    existing.confirmed = False
    existing.unsubscribed_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    existing.tag_preferences = []
    mock_db_session._query_result = [existing]

    with patch("routers.subscribers.send_confirmation_email", return_value=True) as mock_email:
        response = client.post(
            "/api/v1/subscribe",
            json={"email": "returned@example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    mock_email.assert_called_once()
