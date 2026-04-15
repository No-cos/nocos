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
from services.sync import run_scrape, run_description_backfill

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/reactivate")
def reactivate_incorrectly_closed() -> dict:
    """
    Re-activate all tasks currently hidden as 'closed' without making any
    GitHub API calls. Safe to run when the rate limit is exhausted.

    These tasks were hidden by a now-fixed bug in the sync job that couldn't
    find issues by number in page-1 of large repos, so it assumed they were
    closed when they were actually still open.
    """
    from db import SessionLocal
    from models.task import Task
    from datetime import datetime, timezone

    with SessionLocal() as session:
        hidden = (
            session.query(Task)
            .filter(Task.is_active == False, Task.hidden_reason == "closed")
            .all()
        )
        count = 0
        for task in hidden:
            task.is_active = True
            task.hidden_reason = None
            task.hidden_at = None
            count += 1
        session.commit()

    logger.info("Force-reactivated incorrectly closed tasks", extra={"count": count})
    return {"success": True, "reactivated": count}


@router.get("/status")
def sync_status() -> dict:
    """Diagnostic: return DB task/project counts and GitHub rate limit."""
    from db import SessionLocal
    from models.task import Task
    from models.project import Project
    from services.github_client import github_client

    with SessionLocal() as session:
        total_tasks = session.query(Task).count()
        active_tasks = session.query(Task).filter(Task.is_active == True).count()
        hidden_tasks = session.query(Task).filter(Task.is_active == False).count()
        hidden_closed = session.query(Task).filter(
            Task.is_active == False, Task.hidden_reason == "closed"
        ).count()
        total_projects = session.query(Project).count()
        active_projects = session.query(Project).filter(Project.is_active == True).count()

    rate_limit = github_client.get_rate_limit_remaining()

    return {
        "tasks": {"total": total_tasks, "active": active_tasks, "hidden": hidden_tasks, "hidden_closed": hidden_closed},
        "projects": {"total": total_projects, "active": active_projects},
        "github_rate_limit_remaining": rate_limit,
    }


@router.post("/backfill-descriptions")
def backfill_descriptions() -> dict:
    """
    Retry AI description generation for every active task that was stored
    with the fallback string or a too-short body.

    Use this after adding or rotating the ANTHROPIC_API_KEY to retroactively
    generate descriptions for tasks that were ingested while the key was
    missing or invalid.  Safe to call multiple times — tasks that already
    have a real description are skipped automatically.
    """
    logger.info("Manual description backfill triggered")
    try:
        stats = run_description_backfill(SessionLocal)
    except Exception as exc:
        logger.exception("Description backfill endpoint failed")
        return {"success": False, "error": type(exc).__name__, "detail": str(exc)}

    return {
        "success": True,
        "data": {
            "tasks_checked": stats["checked"],
            "descriptions_updated": stats["updated"],
            "skipped_no_key": stats.get("skipped_no_key", False),
            "message": (
                f"Backfill complete. {stats['updated']} description(s) updated "
                f"out of {stats['checked']} candidate task(s) checked."
            ),
        },
    }


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

    try:
        scrape_stats = run_scrape(extra_repos, SessionLocal)
    except Exception as exc:
        logger.exception("Sync trigger failed")
        return {"success": False, "error": type(exc).__name__, "detail": str(exc)}

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
