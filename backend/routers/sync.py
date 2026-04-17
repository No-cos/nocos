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
import threading
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from db import SessionLocal
from services.sync import run_scrape, run_description_backfill, run_discovery

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


@router.post("/trigger-gitlab")
def trigger_gitlab_sync() -> dict:
    """
    Manually trigger a full GitLab scrape in the background.

    Returns 202 immediately — the scrape runs in a daemon thread and can
    take several minutes. Check GET /sync/status for updated task counts.
    Railway's 3-minute proxy timeout means synchronous scrapes of large
    project sets are cut off; fire-and-forget avoids this entirely.
    """
    logger.info("Manual GitLab sync trigger received — starting background thread")

    def _run() -> None:
        try:
            from services.gitlab_sync import run_gitlab_scrape
            run_gitlab_scrape(SessionLocal)
        except Exception:
            logger.exception("Background GitLab scrape failed")

    threading.Thread(target=_run, daemon=True).start()

    return {
        "success": True,
        "accepted": True,
        "message": "GitLab scrape started in background. Check /api/v1/sync/status for updated counts.",
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


@router.post("/trigger-discovery")
def trigger_discovery() -> dict:
    """
    Manually trigger a repo discovery run in the background.

    The discovery job searches GitHub for repos not yet tracked in the DB
    using REPO_DISCOVERY_QUERIES, then scrapes and ingests their non-code issues.

    Returns 202 immediately — the discovery runs in a daemon thread. Use
    GET /sync/status to check updated task/project counts afterwards.
    """
    logger.info("Manual repo discovery trigger received — starting background thread")

    def _run() -> None:
        try:
            run_discovery(SessionLocal)
        except Exception:
            logger.exception("Background repo discovery failed")

    threading.Thread(target=_run, daemon=True).start()

    return {
        "success": True,
        "accepted": True,
        "message": "Repo discovery started in background. Check /api/v1/sync/status for updated counts.",
    }


@router.post("/trigger")
def trigger_sync(body: Optional[SyncTriggerBody] = None) -> dict:
    """
    Manually trigger a full GitHub scrape in the background.

    Returns 202 immediately — the scrape runs in a daemon thread and can
    take several minutes when many projects are tracked. Check GET
    /sync/status for updated task/project counts after a few minutes.

    Railway's proxy timeout is ~3 minutes; synchronous scrapes of large
    project sets are cut off at that boundary. Fire-and-forget avoids this.

    Body (optional JSON):
        { "repos": ["owner/repo", ...] }
    """
    extra_repos = body.repos if body else []

    logger.info(
        "Manual GitHub sync trigger received — starting background thread",
        extra={"extra_repos": extra_repos},
    )

    def _run() -> None:
        try:
            run_scrape(extra_repos, SessionLocal)
        except Exception:
            logger.exception("Background GitHub scrape failed")

    threading.Thread(target=_run, daemon=True).start()

    return {
        "success": True,
        "accepted": True,
        "repos_queued": extra_repos or "all active projects",
        "message": "GitHub scrape started in background. Check /api/v1/sync/status for updated counts.",
    }
