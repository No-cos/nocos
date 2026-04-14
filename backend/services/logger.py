# services/logger.py
# Central logging module for the Nocos backend.
#
# Provides:
#   - get_logger(name)  — returns a named Python logger
#   - mask_email(email) — safe masked form for log messages
#   - JSON formatter for production log aggregation
#   - configure_logging() — called once at app startup (main.py)
#
# Log levels used across the codebase (SKILLS.md §12):
#   INFO    — sync job start/end, issue imported, subscriber added
#   WARNING — rate limit low, AI fallback triggered, email delivery failed
#   ERROR   — API call failed after retries, DB error, unexpected exception
#
# What is NEVER logged:
#   - Email addresses (only masked form: k***@gmail.com)
#   - API keys or tokens
#   - Full request/response bodies from external APIs
#   - Database passwords or connection strings

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


# ── JSON formatter ─────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Each entry includes: timestamp (ISO 8601), level, module, message,
    and any extra context fields passed via the `extra=` kwarg.

    Used in production so log aggregators (Datadog, Papertrail, etc.)
    can parse and index structured fields without regex.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Convert a LogRecord into a JSON string.

        Args:
            record: The log record from Python's logging framework

        Returns:
            Single-line JSON string ending with a newline
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Copy any extra= fields the caller attached to the record
        skip_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in skip_keys:
                entry[key] = value

        # Attach exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger for the given module.

    Usage in any backend module:
        from services.logger import get_logger
        logger = get_logger(__name__)

    This is a thin wrapper around Python's standard logging.getLogger()
    so callers are not coupled to any specific logging library. Switching
    to structlog in the future is a one-file change.

    Args:
        name: Module name — pass __name__ from the calling module

    Returns:
        Configured Python Logger instance
    """
    return logging.getLogger(name)


def mask_email(email: str) -> str:
    """
    Return a masked version of an email address safe for log messages.

    Examples:
        "kingsley@gmail.com"  → "ki***@gmail.com"
        "a@b.com"             → "***@b.com"
        "invalid"             → "***@***"

    Centralised here so the masking logic is consistent across the codebase.
    Previously duplicated in email.py — that module still has its own copy
    for backwards compatibility but new code should import from here.

    Args:
        email: Full email address string

    Returns:
        Masked email string safe for logging
    """
    parts = email.split("@")
    if len(parts) != 2:
        return "***@***"
    local, domain = parts
    masked_local = local[:2] + "***" if len(local) > 2 else "***"
    return f"{masked_local}@{domain}"


def configure_logging(is_production: bool = False) -> None:
    """
    Configure the root logger for the Nocos backend.

    Call this once at application startup (from main.py lifespan handler).

    In development: human-readable text format with timestamps.
    In production:  JSON format so log aggregators can parse structured fields.

    Args:
        is_production: True if APP_ENV == "production"
    """
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers if called more than once
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)

    if is_production:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
