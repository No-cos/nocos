# services/retry.py
# Retry utility with exponential backoff for external API calls.
#
# Applied to: github_client.py, ai/description.py, email.py
#
# Strategy (SKILLS.md §6):
#   - Max 3 attempts per call
#   - Exponential backoff: 1s, 2s, 4s between retries
#   - Each retry is logged at WARNING level with attempt number and reason
#   - After 3 failures: log ERROR with full context, return the fallback value
#   - Never raises to the caller — failures always produce a safe fallback

import logging
import time
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def retry_call(
    func: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    fallback: Any = None,
    context: Optional[dict] = None,
    log: Optional[logging.Logger] = None,
) -> Any:
    """
    Call func up to max_attempts times with exponential backoff.

    Returns the function's return value on success, or `fallback` if all
    attempts fail. Never raises an exception to the caller — callers
    always get a usable value back.

    Backoff schedule (default base_delay=1.0):
        Attempt 1 fails → wait 1s
        Attempt 2 fails → wait 2s
        Attempt 3 fails → log ERROR, return fallback

    Args:
        func:         Zero-argument callable to execute (use lambda or functools.partial)
        max_attempts: Maximum number of attempts before returning fallback (default 3)
        base_delay:   Base sleep duration in seconds — doubled each retry (default 1.0)
        fallback:     Value to return when all attempts fail (default None)
        context:      Dict of extra fields to include in log messages (e.g. {"repo": "..."})
        log:          Logger to use — defaults to the module-level logger

    Returns:
        The return value of func on success, or fallback after max_attempts failures.

    Example:
        result = retry_call(
            lambda: github_client._http.get("/repos/owner/repo"),
            fallback={},
            context={"owner": "chaoss", "repo": "augur"},
            log=logger,
        )
    """
    _log = log or logger
    _ctx = context or {}
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc

            if attempt < max_attempts:
                # Exponential backoff: 1s, 2s, 4s, ...
                delay = base_delay * (2 ** (attempt - 1))
                _log.warning(
                    "External API call failed — retrying",
                    extra={
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "delay_seconds": delay,
                        "error": str(exc),
                        **_ctx,
                    },
                )
                time.sleep(delay)

    # All attempts exhausted — log and return the safe fallback
    _log.error(
        "All retry attempts exhausted — returning safe fallback",
        extra={
            "max_attempts": max_attempts,
            "error": str(last_exc),
            **_ctx,
        },
    )
    return fallback
