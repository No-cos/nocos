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
from services.retry import retry_call

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

    resend.api_key = config.EMAIL_SERVICE_API_KEY
    masked = _mask_email(email)

    def _send() -> None:
        """Single Resend API call — wrapped by retry_call for resilience."""
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": email,
            "subject": "Confirm your Nocos subscription",
            "html": _build_confirmation_html(confirm_url),
        })

    result = retry_call(
        _send,
        fallback=False,
        context={"subscriber": masked},
        log=logger,
    )

    # retry_call returns False (fallback) on failure, None on success (_send returns None)
    # We treat any non-False result (including None from a successful send) as success.
    if result is not False:
        logger.info(
            "Confirmation email sent",
            extra={"subscriber": masked},
        )
        return True

    # retry_call already logged the error — just return False here
    return False


def send_approval_email(email: str, task_title: str, task_url: str) -> bool:
    """
    Send a notification email when an admin approves a manually submitted task.

    Email addresses are never logged — only the masked form is used.

    Args:
        email:      Submitter's email address
        task_title: Title of the approved task
        task_url:   Full URL to the live task on Nocos

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not config.EMAIL_SERVICE_API_KEY:
        logger.warning(
            "EMAIL_SERVICE_API_KEY not set — approval email not sent",
            extra={"submitter": _mask_email(email)},
        )
        return False

    resend.api_key = config.EMAIL_SERVICE_API_KEY
    masked = _mask_email(email)

    def _send() -> None:
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": email,
            "subject": "Your submission to Nocos is live 🎉",
            "html": _build_approval_html(task_title, task_url),
        })

    result = retry_call(
        _send,
        fallback=False,
        context={"submitter": masked},
        log=logger,
    )

    if result is not False:
        logger.info("Approval email sent", extra={"submitter": masked})
        return True

    return False


def send_rejection_email(email: str, task_title: str, reason: str) -> bool:
    """
    Send a notification email when an admin rejects a manually submitted task.

    Includes the rejection reason and a link to the contribution guidelines
    so the submitter can revise and resubmit.

    Email addresses are never logged — only the masked form is used.

    Args:
        email:      Submitter's email address
        task_title: Title of the rejected task
        reason:     Human-readable rejection reason from the admin

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not config.EMAIL_SERVICE_API_KEY:
        logger.warning(
            "EMAIL_SERVICE_API_KEY not set — rejection email not sent",
            extra={"submitter": _mask_email(email)},
        )
        return False

    resend.api_key = config.EMAIL_SERVICE_API_KEY
    masked = _mask_email(email)
    guidelines_url = "https://nocos.cc/guidelines"

    def _send() -> None:
        resend.Emails.send({
            "from": config.EMAIL_FROM,
            "to": email,
            "subject": "Update on your Nocos submission",
            "html": _build_rejection_html(task_title, reason, guidelines_url),
        })

    result = retry_call(
        _send,
        fallback=False,
        context={"submitter": masked},
        log=logger,
    )

    if result is not False:
        logger.info("Rejection email sent", extra={"submitter": masked})
        return True

    return False


def _build_approval_html(task_title: str, task_url: str) -> str:
    """Build the HTML body for the task approval notification email."""
    return f"""
    <html>
      <body style="font-family: Inter, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 24px; color: #0F0F0F;">
        <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #6C3CF7; margin: 0 0 16px;">
          Your issue is live on Nocos 🎉
        </h2>
        <p style="color: #6B6B6B; line-height: 1.6; margin: 0 0 12px;">
          Your submission <strong style="color: #0F0F0F;">"{task_title}"</strong> has been approved and is now live on Nocos.
        </p>
        <p style="color: #6B6B6B; line-height: 1.6; margin: 0 0 24px;">
          Contributors from around the world can now discover and work on your issue.
        </p>
        <a href="{task_url}"
           style="display: inline-block; padding: 12px 24px;
                  background-color: #6C3CF7; color: white; text-decoration: none;
                  border-radius: 8px; font-weight: 600;">
          View your issue on Nocos →
        </a>
        <p style="margin-top: 32px; color: #6B6B6B; line-height: 1.6;">
          Thank you for contributing to the open source community.
        </p>
        <p style="color: #9A9A9A; margin: 0;">— The Nocos team</p>
      </body>
    </html>
    """


def _build_rejection_html(task_title: str, reason: str, guidelines_url: str) -> str:
    """Build the HTML body for the task rejection notification email."""
    return f"""
    <html>
      <body style="font-family: Inter, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 24px; color: #0F0F0F;">
        <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #0F0F0F; margin: 0 0 16px;">
          Update on your Nocos submission
        </h2>
        <p style="color: #6B6B6B; line-height: 1.6; margin: 0 0 12px;">
          Thanks for submitting to Nocos. After review, your submission
          <strong style="color: #0F0F0F;">"{task_title}"</strong>
          wasn't accepted for the following reason:
        </p>
        <p style="background-color: #F9F9F9; border-left: 3px solid #E5E5E5;
                  padding: 12px 16px; border-radius: 0 6px 6px 0;
                  color: #0F0F0F; line-height: 1.6; margin: 0 0 24px;">
          {reason}
        </p>
        <p style="color: #6B6B6B; line-height: 1.6; margin: 0 0 24px;">
          You're welcome to review our contribution guidelines, make any necessary
          adjustments, and resubmit.
        </p>
        <a href="{guidelines_url}"
           style="display: inline-block; padding: 12px 24px;
                  background-color: #6C3CF7; color: white; text-decoration: none;
                  border-radius: 8px; font-weight: 600;">
          Read our guidelines →
        </a>
        <p style="margin-top: 32px; color: #6B6B6B; line-height: 1.6;">
          We appreciate you supporting open source.
        </p>
        <p style="color: #9A9A9A; margin: 0;">— The Nocos team</p>
      </body>
    </html>
    """


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
