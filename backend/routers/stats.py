# routers/stats.py
# Platform statistics endpoint — returns live counts for open tasks,
# active projects, and distinct contribution types.
# Cached in Redis for 5 minutes so the DB isn't queried on every page load.

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import get_db
from models.task import Task
from models.project import Project
from services.cache import app_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])

TTL_STATS = 300  # 5 minutes


@router.get("")
def get_stats(db: Session = Depends(get_db)) -> dict:
    """
    Return platform-wide statistics.

    Counts are computed from live DB state and cached for 5 minutes.

    Returns:
        { open_tasks: int, projects: int, contribution_types: int }
    """
    cache_key = "stats:platform"
    cached = app_cache.get(cache_key)
    if cached:
        return cached

    open_tasks = (
        db.query(func.count(Task.id))
        .filter(Task.is_active == True)
        .scalar() or 0
    )

    projects = (
        db.query(func.count(Project.id))
        .filter(Project.is_active == True)
        .scalar() or 0
    )

    contribution_types = (
        db.query(func.count(func.distinct(Task.contribution_type)))
        .filter(Task.is_active == True)
        .scalar() or 0
    )

    result = {
        "open_tasks": open_tasks,
        "projects": projects,
        "contribution_types": contribution_types,
    }

    app_cache.set(cache_key, result, TTL_STATS)
    return result
