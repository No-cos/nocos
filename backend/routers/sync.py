# routers/sync.py
# Manual trigger endpoint for the Nocos GitHub sync job.
# Allows an operator to kick off a full scrape + ingest without waiting
# for the 6-hour APScheduler interval.
#
# POST /api/v1/sync/trigger
#   - Scrapes all active DB projects for new non-code issues
#   - Optionally seeds new projects via the `repos` body field
#   - Returns a stats envelope so the caller can see what happened

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from db import SessionLocal
from services.sync import run_scrape, run_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncTriggerBody(BaseModel):
    """
    Optional request body for POST /sync/trigger.

    repos: list of "owner/repo" strings to seed into the database.
           Leave empty to only refresh already-tracked projects.

    Example:
        { "repos": ["chaoss/augur", "public-apis/public-apis"] }
    """
    repos: list[str] = []


@router.post("/trigger")
def trigger_sync(body: Optional[SyncTriggerBody] = None) -> dict:
    """
    Manually trigger a full GitHub scrape and freshness sync.

    Two passes run sequentially:
      1. Scrape pass — fetches open non-code issues from GitHub for all
         active projects in the DB plus any repos in the request body.
         Inserts new tasks; skips issues already stored (idempotent).
      2. Freshness pass — checks every existing active task against its
         current GitHub state: hides closed/stale issues, regenerates AI
         descriptions if the issue body changed, recalculates activity scores.

    Returns a stats envelope with counts from both passes.

    Body (optional JSON):
        { "repos": ["owner/repo", ...] }
    """
    extra_repos = body.repos if body else []

    logger.info(
        "Manual sync trigger received",
        extra={"extra_repos": extra_repos},
    )

    # Pass 1: scrape new issues (and seed new projects if repos were provided)
    try:
        scrape_stats = run_scrape(extra_repos, SessionLocal)
    except Exception as exc:
        logger.exception("Sync trigger scrape pass failed")
        return {"success": False, "error": type(exc).__name__, "detail": str(exc)}

    # Pass 2: freshen existing tasks / projects
    run_sync(SessionLocal)

    return {
        "success": True,
        "data": {
            "projects_scraped": scrape_stats["projects_scraped"],
            "new_tasks_added": scrape_stats["new_tasks_added"],
            "scrape_duration_seconds": scrape_stats["duration_seconds"],
            "message": (
                f"Sync complete. {scrape_stats['new_tasks_added']} new task(s) added "
                f"across {scrape_stats['projects_scraped']} project(s)."
            ),
        },
    }
