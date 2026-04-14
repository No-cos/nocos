# services/email.py
# Email sending service for Nocos.
# Handles subscriber confirmation emails and weekly digest delivery.
# Uses Resend as the email provider — swap EMAIL_PROVIDER in config to
# switch without touching this module's public interface.
#
# Email addresses are never logged (SKILLS.md Section 12).
# The masked format (k***@gmail.com) is used where references are needed.

import logging
import re
from typing import Optional

import resend

from config import config

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """
    Return a masked version of an email address safe for logging.

    e.g. "kingsley@gmail.com" → "ki***@gmail.com"

    Args:
        email: Full email address string

    Returns:
        Masked email with local part truncated after 2 characters
    """
    parts = email.split("@")
    if len(parts) != 2:
        return "***@***"
    local, domain = parts
    masked_local = local[:2] + "***" if len(local) > 2 else "***"
    return f"{masked_local}@{domain}"


def send_confirmation_email(email: str, subscriber_id: str) -> bool:
    """
    Send a double opt-in confirmation email to a new subscriber.

    The confirmation link includes the subscriber UUID as a token.
    Clicking it sets confirmed=True in the database (handled by a
    separate endpoint added in Phase 3).

    Email addresses are never logged — only the masked form is used.

    Args:
        email:         Recipient email address
        subscriber_id: Subscriber UUID used as the confirmation token

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not config.EMAIL_SERVICE_API_KEY:
        # No email key configured — common in local development.
        # Log a clear message rather than raising so the subscription
        # still completes and the subscriber record is created.
        logger.warning(
            "EMAIL_SERVICE_API_KEY not set — confirmation email not sent",
            extra={"subscriber": _mask_email(email)},
        )
        return False

    confirm_url = (
        f"{config.NEXT_PUBLIC_API_URL}/api/v1/subscribe/confirm/{subscriber_id}"
    )

    try:
        resend.api_key = config.EMAIL_SERVICE_API_KEY
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": email,
            "subject": "Confirm your Nocos subscription",
            "html": _build_confirmation_html(confirm_url),
        })

        logger.info(
            "Confirmation email sent",
            extra={"subscriber": _mask_email(email)},
        )
        return True

    except Exception as e:
        # Email delivery failure should not block the subscription API response.
        # The subscriber record is already created — they can re-trigger later.
        logger.error(
            "Failed to send confirmation email",
            extra={"subscriber": _mask_email(email), "error": str(e)},
        )
        return False


def _build_confirmation_html(confirm_url: str) -> str:
    """
    Build the HTML body for the subscription confirmation email.

    Kept inline here rather than in a template file to avoid a file I/O
    dependency in the email service. Move to Jinja2 templates in Phase 7
    when the digest email requires more complex templating.

    Args:
        confirm_url: The full confirmation URL including the subscriber token

    Returns:
        HTML string for the email body
    """
    return f"""
    <html>
      <body style="font-family: Inter, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 24px; color: #0F0F0F;">
        <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #6C3CF7;">
          Confirm your subscription to Nocos
        </h2>
        <p style="color: #6B6B6B; line-height: 1.6;">
          You're one step away from getting curated non-code open source tasks
          delivered to your inbox every week.
        </p>
        <a href="{confirm_url}"
           style="display: inline-block; margin-top: 24px; padding: 12px 24px;
                  background-color: #6C3CF7; color: white; text-decoration: none;
                  border-radius: 8px; font-weight: 600;">
          Confirm my subscription →
        </a>
        <p style="margin-top: 32px; font-size: 12px; color: #9A9A9A;">
          If you didn't subscribe to Nocos, you can safely ignore this email.
        </p>
      </body>
    </html>
    """
