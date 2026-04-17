# routers/featured.py
# GET /api/v1/featured — returns two curated project lists for the
# "Featured Projects" section on the Nocos homepage.
#
# Response shape:
#   {
#     "success": true,
#     "data": {
#       "most_active":   [FeaturedProjectResponse, ...],   # up to 6
#       "new_promising": [FeaturedProjectResponse, ...]    # up to 6
#     }
#   }
#
# Data flow (DB-first, service fallback):
#   1. Query featured_projects table for the most recent week_of value.
#   2. If rows exist → serialise and return them (fast path, no GitHub calls).
#   3. If table is empty (e.g. first deploy before the scheduler has run) →
#      call the service functions live, which hit GitHub Search and cache in Redis.
#
# The weekly APScheduler job (Sunday 00:00 UTC) keeps the DB fresh so the live
# fallback path is only ever hit on a cold first boot.

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.featured_project import FeaturedProject

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/featured", tags=["featured"])


def _serialise(fp: FeaturedProject) -> dict:
    """Convert a FeaturedProject ORM row to the API response dict."""
    return {
        "repo_full_name": fp.repo_full_name,
        "name": fp.name,
        "description": fp.description,
        "language": fp.language,
        "stars": fp.stars,
        "stars_gained_this_week": fp.stars_gained_this_week,
        "forks": fp.forks,
        "open_issues_count": fp.open_issues_count,
        "homepage": fp.homepage,
        "license": fp.license,
        "topics": fp.topics or [],
        "weekly_commits": fp.weekly_commits,
        "avatar_url": fp.avatar_url,
        "github_url": fp.github_url,
        "category": fp.category,
    }


@router.get("")
def get_featured(db: Session = Depends(get_db)) -> dict:
    """
    Return the two featured project lists.

    Reads from the DB first. If the featured_projects table is empty
    (first deploy or scheduler hasn't run yet), falls back to live GitHub
    Search results via the service layer.

    Returns:
        Envelope: { success, data: { most_active, new_promising } }
    """
    # ── DB-first path ──────────────────────────────────────────────────────────
    # Find the most recent week_of so we always return the latest snapshot,
    # not stale rows from a prior week.
    latest_week = (
        db.query(FeaturedProject.week_of)
        .order_by(FeaturedProject.week_of.desc())
        .limit(1)
        .scalar()
    )

    if latest_week is not None:
        rows = (
            db.query(FeaturedProject)
            .filter(FeaturedProject.week_of == latest_week)
            .all()
        )

        most_active = [_serialise(r) for r in rows if r.category == "most_active"]
        new_promising = [_serialise(r) for r in rows if r.category == "new_promising"]

        logger.info(
            "Featured projects served from DB",
            extra={
                "week_of": str(latest_week),
                "most_active": len(most_active),
                "new_promising": len(new_promising),
            },
        )

        return {
            "success": True,
            "data": {
                "most_active": most_active,
                "new_promising": new_promising,
            },
        }

    # ── Live fallback (table empty) ────────────────────────────────────────────
    # This path is taken on first deploy before the scheduler has run.
    # Results are cached in Redis by the service functions so subsequent requests
    # are fast even if the DB is still empty.
    logger.info("Featured projects table is empty — fetching live from GitHub")

    from services.featured_projects_service import (
        fetch_most_active_projects,
        fetch_new_promising_projects,
    )

    most_active = fetch_most_active_projects()
    new_promising = fetch_new_promising_projects()

    return {
        "success": True,
        "data": {
            "most_active": most_active,
            "new_promising": new_promising,
        },
    }
