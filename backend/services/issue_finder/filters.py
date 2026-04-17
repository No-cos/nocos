# services/issue_finder/filters.py
# Filtering logic for scraped GitHub issues.
# This module decides which issues are worth storing and displaying.
# It is deliberately stateless — it takes dicts and returns bools,
# which makes every function straightforward to unit test.
#
# Filters applied in sequence by should_include_issue():
#   1.  Code-only label check  — skip issues whose every label is code-specific
#   1b. Code title prefix      — skip "fix:", "feat:", "refactor:", etc. titles
#   1c. Catch-all without signal — skip help-wanted/good-first-issue issues
#                                  that contain no non-code contribution signals
#   2.  Age check              — skip issues older than MAX_ISSUE_AGE_DAYS
#   3.  Status check           — skip closed issues

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Issues older than this are considered stale and should not be imported.
MAX_ISSUE_AGE_DAYS = 28

# Labels that indicate purely code-specific work.
# An issue whose EVERY label is in this set has no non-code contribution angle.
# If a code label appears alongside a non-code label (e.g. "bug" + "design")
# the issue still passes — the design work is what Nocos cares about.
CODE_ONLY_LABELS = frozenset({
    "bug",
    "feature",
    "enhancement",
    "refactor",
    "performance",
    "security",
    "regression",
    "crash",
    "build",
    "ci",
    "tests",
    "testing",
    "backend",
    "frontend",
    "api",
    "database",
    "dependencies",
    "dependencies-update",
    "chore",
    "wontfix",
    "duplicate",
    "invalid",
    "question",
})

# Conventional commit title prefixes — unambiguously code-only work.
CODE_TITLE_PREFIXES: tuple[str, ...] = (
    "fix:",
    "feat:",
    "refactor:",
    "chore:",
    "build:",
    "ci:",
    "perf:",
    "test:",
    "tests:",
)

# Labels that invite contributors without specifying the type of work.
# Issues with ONLY these labels (and no specific non-code label) must contain
# a non-code signal in the title or body to be ingested.
CATCH_ALL_LABELS = frozenset({
    "help-wanted",
    "help wanted",
    "good-first-issue",
    "good first issue",
    "first-timers-only",
    "hacktoberfest",
    "up-for-grabs",
    "contributions-welcome",
    "beginner-friendly",
    "low-hanging-fruit",
})

# Labels that explicitly signal non-code contribution work.
# An issue with any of these passes the catch-all filter regardless of body.
SPECIFIC_NON_CODE_LABELS = frozenset({
    # Design
    "design", "needs-design", "ux", "ui", "ui/ux", "design-needed",
    "figma", "visual", "accessibility", "a11y",
    # Documentation
    "documentation", "docs", "needs-docs", "improve-docs", "doc-fix",
    "good-docs", "writing", "content", "technical-writing",
    # Translation
    "translation", "i18n", "l10n", "localization", "internationalisation",
    "needs-translation", "language",
    # Research
    "research", "user-research", "needs-research", "investigation", "discovery",
    # Community
    "community", "community-management", "outreach", "social", "devrel",
    "developer-relations", "advocacy",
    # Marketing
    "marketing", "growth", "content-marketing", "seo", "copywriting",
    # Social Media
    "social-media", "twitter", "announcement",
    # Project Management
    "project-management", "planning", "roadmap",
    "triage", "needs-triage", "organisation",
    # PR Review
    "needs-review", "pr-review", "review-needed", "review-requested",
    # Data & Analytics
    "analytics", "data", "metrics", "tracking", "data-analysis",
})

# Individual words that indicate non-code contribution work.
# Checked at word boundaries so short terms like "ux" don't fire inside
# longer words like "luxury" or "auxiliary".
_NON_CODE_SIGNAL_WORDS = frozenset({
    # Design
    "design", "figma", "ux", "accessibility", "a11y", "mockup",
    "wireframe", "visual", "prototype", "icon", "logo", "typography",
    "illustration", "banner", "screenshot", "branding", "colours", "colors",
    "theme", "palette", "sketch", "invision", "zeplin",
    # Documentation
    "documentation", "docs", "readme", "wiki", "writing", "content",
    "markdown", "tutorial", "guide", "changelog", "glossary", "handbook",
    "runbook", "playbook", "faq", "howto", "onboarding", "walkthrough",
    "explainer", "example", "examples", "template", "templates",
    # Translation
    "translation", "translate", "locale", "localization", "i18n", "l10n",
    "internationalisation", "internationalization", "subtitles", "captions",
    # Community
    "community", "outreach", "advocacy", "devrel", "newsletter", "announcement",
    "forum", "discord", "slack", "contributor", "contributors", "mentoring",
    "mentorship", "welcoming", "inclusion", "diversity",
    # Marketing
    "marketing", "seo", "copywriting", "campaign", "landing", "homepage",
    "website", "tagline", "messaging", "brochure",
    # Research
    "research", "survey", "usability", "feedback", "interview", "personas",
    "journey", "painpoints", "discovery",
    # Analytics
    "analytics", "metrics", "tracking", "dashboard", "kpi", "reporting",
    # Project management / process
    "triage", "roadmap", "planning", "prioritisation", "prioritization",
    "checklist", "workflow", "process", "coordination",
    # General non-code signals
    "podcast", "blog", "conference", "meetup", "event", "webinar",
    "presentation", "slides", "video", "demo", "showcase",
})

# Multi-word phrases checked via substring match.
_NON_CODE_SIGNAL_PHRASES = frozenset({
    "user research",
    "technical writing",
    "social media",
    "developer relations",
    "content marketing",
    "data analysis",
    "open graph",
    "style guide",
    # Additional phrases added during filter review
    "onboarding guide",
    "contribution guide",
    "contribution guidelines",
    "getting started",
    "project management",
    "community management",
    "press release",
    "case study",
    "best practices",
    "design system",
    "information architecture",
})


def has_code_title_prefix(title: str) -> bool:
    """
    Return True if the issue title starts with a conventional commit prefix.

    Titles like "fix: null pointer in auth", "feat: add OAuth" are
    unambiguously code work and must never appear on Nocos.

    Args:
        title: The issue title string

    Returns:
        True if the title starts with a code-only conventional commit prefix.
    """
    lower = title.lower().strip()
    return any(lower.startswith(prefix) for prefix in CODE_TITLE_PREFIXES)


def _has_non_code_signal(issue: dict) -> bool:
    """
    Return True if the title or body contains a non-code contribution signal.

    Used as a secondary gate for issues that carry only catch-all labels
    (e.g. "help-wanted" with no other labels). Looks for specific non-code
    keywords at word boundaries to avoid false positives from substrings.

    Args:
        issue: Structured issue dict with "title" and "body" keys

    Returns:
        True if at least one non-code signal word or phrase was found.
    """
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    text = title + " " + body

    for phrase in _NON_CODE_SIGNAL_PHRASES:
        if phrase in text:
            return True

    words = frozenset(re.findall(r"\b\w+\b", text))
    return bool(words & _NON_CODE_SIGNAL_WORDS)


def is_catch_all_only_without_signal(issue: dict) -> bool:
    """
    Return True if the issue should be rejected because it only carries
    catch-all labels and its title/body contains no non-code signals.

    Decision tree:
    - Any SPECIFIC_NON_CODE_LABELS present → allow (return False)
    - Labels are only CATCH_ALL_LABELS + CODE_ONLY_LABELS (or empty) →
        allow only if a non-code signal word/phrase is present in title/body
    - Otherwise → allow (return False)

    This prevents "help-wanted: fix the memory leak" from being ingested
    while still passing "help-wanted: improve the translation workflow".

    Args:
        issue: Structured issue dict with "labels", "title", and "body" keys

    Returns:
        True if the issue should be rejected.
    """
    normalised = {lbl.lower() for lbl in issue.get("labels", [])}

    # Any specific non-code label → always allow
    if normalised & SPECIFIC_NON_CODE_LABELS:
        return False

    # Only catch-alls (possibly mixed with code-only labels) → require signal
    if normalised.issubset(CATCH_ALL_LABELS | CODE_ONLY_LABELS):
        return not _has_non_code_signal(issue)

    return False


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

    Issues older than MAX_ISSUE_AGE_DAYS are considered stale and excluded.
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
    title = issue.get("title", "")

    # Filter 1: all labels are code-specific
    if has_only_code_labels(labels):
        logger.debug(
            "Filtered — code-only labels",
            extra={"issue_id": issue.get("github_issue_id"), "labels": labels},
        )
        return False

    # Filter 1b: title starts with a conventional commit code prefix
    if has_code_title_prefix(title):
        logger.debug(
            "Filtered — code-only title prefix",
            extra={"issue_id": issue.get("github_issue_id"), "title": title},
        )
        return False

    # Filter 1c: catch-all labels only and no non-code signal in title/body
    if is_catch_all_only_without_signal(issue):
        logger.debug(
            "Filtered — catch-all labels with no non-code signal",
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
