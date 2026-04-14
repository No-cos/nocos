# services/issue_finder/filters.py
# Filtering logic for scraped GitHub issues.
# This module decides which issues are worth storing and displaying.
# It is deliberately stateless — it takes dicts and returns bools,
# which makes every function straightforward to unit test.
#
# Three filters are applied in sequence by should_include_issue():
#   1. Code-only label check — skip issues that only have dev-specific labels
#   2. Age check           — skip issues older than 14 days (features.md §7)
#   3. Status check        — skip issues that are already closed

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Issues older than this are considered stale and should not be imported.
# This matches the 14-day staleness rule in features.md Section 7.
MAX_ISSUE_AGE_DAYS = 14

# Labels that indicate purely code-specific work.
# An issue with ONLY these labels has no non-technical contribution angle.
# If a code label appears alongside a non-code label (e.g. "bug" + "design")
# we still include it — the design work is what we care about.
CODE_ONLY_LABELS = frozenset({
    "bug",
    "feature",
    "enhancement",
    "wontfix",
    "duplicate",
    "invalid",
    "question",
    "help wanted",  # Ambiguous — included here as a conservative default
})


def has_only_code_labels(labels: list[str]) -> bool:
    """
    Return True if every label on an issue is a code-specific label.

    We keep issues that have at least one non-code label mixed in.
    This function returns True only when ALL labels are in the code-only set —
    meaning there is no non-code angle to the issue at all.

    Args:
        labels: List of GitHub label name strings (case-insensitive comparison)

    Returns:
        True if all labels are code-only and the issue should be filtered out.
    """
    if not labels:
        # No labels — could be anything, give it the benefit of the doubt
        return False

    normalised = {lbl.lower() for lbl in labels}
    # If any label is NOT in the code-only set, the issue has a non-code angle
    return normalised.issubset(CODE_ONLY_LABELS)


def is_too_old(github_created_at: Optional[datetime]) -> bool:
    """
    Return True if an issue is older than MAX_ISSUE_AGE_DAYS.

    Issues beyond 14 days are considered stale per features.md Section 7.
    None is treated as an unknown date and allowed through — better to
    include an issue with a missing date than to silently drop it.

    Args:
        github_created_at: The issue's creation datetime (timezone-aware)

    Returns:
        True if the issue is older than the cutoff and should be filtered out.
    """
    if github_created_at is None:
        # Unknown creation date — allow through rather than silently drop
        return False

    # Ensure the datetime is timezone-aware before comparing
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=MAX_ISSUE_AGE_DAYS)

    if github_created_at.tzinfo is None:
        # Treat naive datetimes as UTC — GitHub always returns UTC
        github_created_at = github_created_at.replace(tzinfo=timezone.utc)

    return github_created_at < cutoff


def is_closed(state: str) -> bool:
    """
    Return True if the issue is closed.

    We only import open issues. Closed issues found during the freshness
    sync are handled separately — they update existing DB records rather
    than being filtered at import time.

    Args:
        state: The GitHub issue state string (e.g. "open", "closed")

    Returns:
        True if the issue is closed and should be skipped.
    """
    return state.lower() != "open"


def should_include_issue(issue: dict) -> bool:
    """
    Return True if a scraped issue should be imported into the Nocos database.

    Applies all three filters in sequence. Logs the reason when an issue is
    excluded so we can monitor filter rates over time.

    Args:
        issue: A structured issue dict as returned by scraper.scrape_issues_for_label()

    Returns:
        True if the issue passes all filters and should be stored.
    """
    labels = issue.get("labels", [])
    created_at = issue.get("github_created_at")
    state = issue.get("state", "open")

    # Filter 1: code-only labels
    if has_only_code_labels(labels):
        logger.debug(
            "Filtered — code-only labels",
            extra={"issue_id": issue.get("github_issue_id"), "labels": labels},
        )
        return False

    # Filter 2: too old
    if is_too_old(created_at):
        logger.debug(
            "Filtered — older than 14 days",
            extra={"issue_id": issue.get("github_issue_id"), "created_at": str(created_at)},
        )
        return False

    # Filter 3: closed
    if is_closed(state):
        logger.debug(
            "Filtered — issue is closed",
            extra={"issue_id": issue.get("github_issue_id")},
        )
        return False

    return True


def apply_filters(issues: list[dict]) -> list[dict]:
    """
    Apply should_include_issue() to a list and return only passing issues.

    Convenience wrapper used by the enricher and sync modules to filter
    a full batch of scraped issues in one call.

    Args:
        issues: List of structured issue dicts from the scraper

    Returns:
        Filtered list containing only issues that passed all checks.
    """
    before = len(issues)
    filtered = [i for i in issues if should_include_issue(i)]
    after = len(filtered)

    if before != after:
        logger.info(
            "Filter pass complete",
            extra={"before": before, "after": after, "removed": before - after},
        )

    return filtered


def should_hide_issue(issue: dict) -> bool:
    """
    Return True if an existing DB issue should be hidden during a freshness sync.

    Used by the sync job (sync.py) to check already-imported issues against
    the freshness rules. Unlike should_include_issue(), this is called on issues
    that are already in the database — it checks whether they should remain visible.

    Args:
        issue: Dict with at least "github_created_at" (datetime) and "status" (str)

    Returns:
        True if the issue should have is_active set to False.
    """
    created_at = issue.get("github_created_at")
    status = issue.get("status", "open")

    if is_closed(status):
        return True

    if is_too_old(created_at):
        return True

    return False
