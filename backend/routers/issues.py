# routers/issues.py
# API endpoints for issue (task) discovery and submission.
# Phase 1: Returns stub responses. Full implementation in Phase 2.
# TODO: Connect to database queries after Phase 2 — see models/task.py

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("")
async def list_issues(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(12, ge=1, le=50, description="Results per page (max 50)"),
    type: Optional[str] = Query(None, description="Filter by contribution type"),
    types: Optional[str] = Query(None, description="Comma-separated contribution types"),
    search: Optional[str] = Query(None, description="Search by project name, title, or type"),
    paid: Optional[bool] = Query(None, description="Filter by paid status"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
) -> dict:
    """
    List active issues with optional filtering and pagination.

    Returns 12 issues per page by default, sorted by most recent.
    Supports multi-type filtering via the types param (comma-separated).
    Hidden issues (stale, closed, archived) are never included.
    """
    # Phase 1 stub — returns empty list until Phase 2 connects the database
    return {
        "success": True,
        "data": [],
        "meta": {
            "page": page,
            "total": 0,
            "per_page": limit,
        },
    }


@router.get("/{issue_id}")
async def get_issue(issue_id: str) -> dict:
    """
    Get a single issue with full project details.

    Used by the task detail page to display the full description,
    project info, and related issues from the same project.
    """
    # Phase 1 stub — full implementation in Phase 2
    return {
        "success": False,
        "error": "Not implemented yet",
        "code": "NOT_IMPLEMENTED",
    }


@router.post("")
async def create_issue(body: dict) -> dict:
    """
    Manually post a task (maintainer submission).

    Validates the request, fetches project info from GitHub if a repo URL
    is provided, and creates a new task with source=manual_post.
    Full implementation in Phase 5.
    """
    # Phase 1 stub — full implementation in Phase 5
    return {
        "success": False,
        "error": "Not implemented yet",
        "code": "NOT_IMPLEMENTED",
    }
