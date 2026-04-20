# services/issue_finder/enricher.py
# Enriches filtered issues before they are written to the database.
# Enrichment means: decide whether the issue needs an AI description,
# fetch the first 3 comments for context if it does, then call Claude.
#
# This module is called after the filter pass — it only processes issues
# that have already been deemed worth keeping. Separating enrichment from
# scraping keeps each module's responsibility clear and individually testable.

import logging
import time
from typing import Optional

from services.ai.description import generate_enrichment, needs_ai_description
from services.github_client import github_client

logger = logging.getLogger(__name__)

# Maximum number of consecutive enrichment failures before we abort a batch.
# Protects against runaway Anthropic API costs if something goes wrong.
MAX_CONSECUTIVE_FAILURES = 10

# Delay between AI generation calls in seconds.
# Anthropic's rate limit is generous but we add a small pause to avoid
# bursting and to keep token costs predictable.
AI_CALL_DELAY_SECONDS = 0.5


def enrich_issue(issue: dict, repo_description: str = "") -> dict:
    """
    Enrich a single filtered issue with a display description.

    Checks whether the issue body meets the 20-word minimum. If not, fetches
    the first 3 comments for context and calls Claude to generate a plain-
    English description.

    The returned dict is the same as the input dict with two fields added:
      - description_display (str):  what contributors will read
      - is_ai_generated (bool):     True if Claude wrote the description

    Args:
        issue:            Structured issue dict from the scraper/filter pipeline
        repo_description: The GitHub repo description — passed to Claude as context

    Returns:
        The same issue dict with description_display and is_ai_generated set.
    """
    body = issue.get("body")
    owner = issue.get("github_owner", "")
    repo = issue.get("github_repo", "")
    issue_number = issue.get("github_issue_number")

    # Fetch comments only when we actually need them — avoids unnecessary API calls
    first_comments: list[str] = []
    if needs_ai_description(body) and owner and repo and issue_number:
        first_comments = github_client.get_issue_comments(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            limit=3,
        )

    result = generate_enrichment(
        body=body,
        repo_name=f"{owner}/{repo}",
        repo_description=repo_description,
        issue_title=issue.get("title", ""),
        labels=issue.get("labels", []),
        first_comments=first_comments,
    )

    enriched = {**issue}
    enriched["ai_title"] = result["ai_title"]
    enriched["description_display"] = result["description_display"]
    enriched["is_ai_generated"] = result["is_ai_generated"]

    if result["ai_title"] or result["is_ai_generated"]:
        logger.info(
            "AI enrichment applied to issue",
            extra={
                "github_issue_id": issue.get("github_issue_id"),
                "repo": f"{owner}/{repo}",
                "ai_title": result["ai_title"] is not None,
                "ai_description": result["is_ai_generated"],
            },
        )

    return enriched


def enrich_issues(
    issues: list[dict],
    repo_description: str = "",
) -> list[dict]:
    """
    Enrich a batch of filtered issues.

    Processes issues sequentially with a small delay between AI calls.
    If MAX_CONSECUTIVE_FAILURES is reached, enrichment stops and the
    remaining issues are returned with their fallback descriptions already
    set by process_issue_description().

    Args:
        issues:           List of filtered issue dicts
        repo_description: GitHub repo description passed to Claude for context

    Returns:
        List of enriched issue dicts. Every issue will have
        description_display and is_ai_generated set.
    """
    enriched_issues: list[dict] = []
    consecutive_failures = 0

    for issue in issues:
        try:
            enriched = enrich_issue(issue, repo_description=repo_description)
            enriched_issues.append(enriched)
            consecutive_failures = 0

            # Pace AI generation calls — small delay avoids burst behaviour
            if enriched.get("is_ai_generated"):
                time.sleep(AI_CALL_DELAY_SECONDS)

        except Exception as e:
            # A single enrichment failure must not abort the whole batch.
            # The fallback description is already safe — log and continue.
            consecutive_failures += 1
            logger.error(
                "Issue enrichment failed — using fallback description",
                extra={
                    "github_issue_id": issue.get("github_issue_id"),
                    "error": str(e),
                    "consecutive_failures": consecutive_failures,
                },
            )
            # Add the issue with fallback description so it still gets stored
            fallback = {**issue}
            fallback["ai_title"] = None
            fallback["description_display"] = "Visit GitHub for full details on this task."
            fallback["is_ai_generated"] = False
            enriched_issues.append(fallback)

            # Abort if we're seeing sustained failures — likely an API outage
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    "Too many consecutive enrichment failures — aborting batch",
                    extra={"remaining": len(issues) - len(enriched_issues)},
                )
                # Add remaining issues with fallback so none are silently dropped
                for remaining in issues[len(enriched_issues):]:
                    fallback = {**remaining}
                    fallback["ai_title"] = None
                    fallback["description_display"] = "Visit GitHub for full details on this task."
                    fallback["is_ai_generated"] = False
                    enriched_issues.append(fallback)
                break

    logger.info(
        "Enrichment batch complete",
        extra={
            "total": len(issues),
            "ai_generated": sum(1 for i in enriched_issues if i.get("is_ai_generated")),
        },
    )
    return enriched_issues


def should_regenerate_description(
    stored_body: Optional[str],
    current_body: Optional[str],
) -> bool:
    """
    Return True if the AI description should be regenerated.

    Regeneration is triggered when the original GitHub issue body has changed
    since we last stored it (features.md Section 5). We compare the raw body
    strings — any change at all triggers regeneration on the next sync.

    Args:
        stored_body:  The description_original value in our database
        current_body: The current body fetched from GitHub during sync

    Returns:
        True if the description should be regenerated.
    """
    # Treat None and empty string as equivalent — GitHub sometimes returns
    # null for empty bodies and sometimes returns an empty string
    normalise = lambda s: (s or "").strip()
    return normalise(stored_body) != normalise(current_body)
