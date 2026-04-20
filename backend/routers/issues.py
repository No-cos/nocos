# routers/issues.py
# REST API endpoints for issue (task) discovery and manual submission.
# All queries filter by is_active=True so hidden/stale/closed issues
# never appear in any response.

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from db import get_db
from models.task import Task
from models.project import Project
from schemas.issue import IssueCreateRequest
from services.cache import app_cache, TTL_ISSUE_DETAIL, TTL_ISSUE_LIST
from services.issue_finder.filters import MAX_ISSUE_AGE_DAYS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])

# Default and maximum page sizes
DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50


def _build_issue_response(task: Task) -> dict:
    """
    Serialise a Task ORM object into the API response envelope format.

    Embeds a ProjectSummary so the card can render without a second request.
    description_original is never included — only description_display (SKILLS.md §16).

    Args:
        task: Task ORM object with project relationship loaded

    Returns:
        Dict matching the IssueResponse schema
    """
    project = task.project
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "project": {
            "id": str(project.id),
            "name": project.name,
            "avatar_url": project.avatar_url,
            "activity_status": project.activity_status,
            "github_owner": project.github_owner,
            "github_repo": project.github_repo,
        },
        "title": task.title,
        "ai_title": task.ai_title,  # null when enrichment hasn't run yet
        "description_display": task.description_display,
        "is_ai_generated": task.is_ai_generated,
        "labels": task.labels or [],
        "contribution_type": task.contribution_type,
        "is_paid": task.is_paid,
        "is_bounty": task.is_bounty if task.is_bounty is not None else False,
        "bounty_amount": task.bounty_amount,
        "difficulty": task.difficulty,
        "source": task.source,
        "github_issue_url": task.github_issue_url,
        "github_created_at": task.github_created_at.isoformat() if task.github_created_at else None,
        "is_active": task.is_active,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


@router.get("")
def list_issues(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Results per page"),
    type: Optional[str] = Query(None, description="Filter by single contribution type"),
    types: Optional[str] = Query(None, description="Comma-separated contribution types"),
    search: Optional[str] = Query(None, description="Search by project name, title, or type"),
    paid: Optional[bool] = Query(None, description="Filter by paid status"),
    bounty: Optional[bool] = Query(None, description="Filter to only bounty issues (is_bounty=true)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: beginner|intermediate|advanced"),
    db: Session = Depends(get_db),
) -> dict:
    """
    List active issues with optional filtering and pagination.

    Returns issues sorted by created_at descending (most recent first).
    Hidden issues (stale, closed, archived) are always excluded.
    Supports single-type filter via ?type= or multi-type via ?types=design,docs.

    Returns:
        Envelope: { success, data: [IssueResponse], meta: { page, total, per_page } }
    """
    # Issues older than MAX_ISSUE_AGE_DAYS are excluded at query time so that
    # pagination counts are accurate and no page ever returns fewer items than
    # requested. Manually posted tasks (github_created_at IS NULL) always pass.
    age_cutoff = datetime.now(tz=timezone.utc) - timedelta(days=MAX_ISSUE_AGE_DAYS)

    query = (
        db.query(Task)
        .join(Task.project)
        .options(joinedload(Task.project))
        .filter(Task.is_active == True)
        .filter(Task.review_status == "approved")
        .filter(Project.is_active == True)
        .filter(
            (Task.github_created_at == None) | (Task.github_created_at >= age_cutoff)
        )
    )

    # Contribution type filter — supports both ?type= and ?types= params
    type_filter: list[str] = []
    if type:
        type_filter = [type.strip()]
    elif types:
        type_filter = [t.strip() for t in types.split(",") if t.strip()]

    if type_filter:
        query = query.filter(Task.contribution_type.in_(type_filter))

    # Paid filter
    if paid is not None:
        query = query.filter(Task.is_paid == paid)

    # Bounty filter — shows only issues with a real-money reward attached
    if bounty is not None:
        query = query.filter(Task.is_bounty == bounty)

    # Difficulty filter
    if difficulty:
        query = query.filter(Task.difficulty == difficulty)

    # Search — matches against issue title or project name (case-insensitive)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Project.name.ilike(search_term),
                Task.contribution_type.ilike(search_term),
            )
        )

    # Total count before pagination (for the meta block)
    total = query.count()

    # Sort by GitHub issue creation date (newest first), with nulls last so
    # manually posted tasks (github_created_at IS NULL) don't surface above
    # real issues. Pagination is applied after ORDER BY for consistent pages.
    tasks = (
        query
        .order_by(Task.github_created_at.desc().nullslast())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "data": [_build_issue_response(t) for t in tasks],
        "meta": {
            "page": page,
            "total": total,
            "per_page": limit,
        },
    }


@router.get("/{issue_id}")
def get_issue(issue_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Get a single active issue with full project details.

    Checks the Redis cache first (TTL 30 min) before hitting the database.
    Cache key: issue:{issue_id}. Cache is invalidated by the sync job when
    the issue description is regenerated.

    Used by the task detail page. Returns the full project object (not just
    a summary) so the "About This Project" section can render without a
    separate /projects/:id call.

    Args:
        issue_id: UUID of the issue

    Returns:
        Envelope: { success, data: IssueResponse with full project }

    Raises:
        404 if the issue does not exist or is not active
    """
    try:
        uid = UUID(issue_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check cache before querying the database — detail pages are the highest
    # traffic single-item endpoint and benefit most from caching
    cache_key = f"issue:{issue_id}"
    cached = app_cache.get(cache_key)
    if cached:
        return cached

    task = (
        db.query(Task)
        .options(joinedload(Task.project))
        .filter(Task.id == uid, Task.is_active == True, Task.review_status == "approved")
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Issue not found", "code": "ISSUE_NOT_FOUND"},
        )

    # Build full project response (not the summary variant)
    project = task.project
    full_project = {
        "id": str(project.id),
        "name": project.name,
        "github_url": project.github_url,
        "github_owner": project.github_owner,
        "github_repo": project.github_repo,
        "description": project.description,
        "website_url": project.website_url,
        "avatar_url": project.avatar_url,
        "social_links": project.social_links,
        "activity_score": project.activity_score,
        "activity_status": project.activity_status,
        "last_commit_date": project.last_commit_date.isoformat() if project.last_commit_date else None,
        "is_active": project.is_active,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }

    issue_data = _build_issue_response(task)
    issue_data["project"] = full_project

    response = {"success": True, "data": issue_data}
    # Store in cache for 30 minutes — invalidated by sync job on description update
    app_cache.set(cache_key, response, TTL_ISSUE_DETAIL)
    return response


@router.post("")
def create_issue(body: IssueCreateRequest, db: Session = Depends(get_db)) -> dict:
    """
    Manually post a task (maintainer submission).

    Validates the request body with Pydantic, fetches project info from
    GitHub using the repo URL, and creates a Task with source=manual_post.
    Manual tasks follow the same 14-day staleness rule as scraped tasks.

    Returns:
        Envelope: { success, data: { id, message } }

    Raises:
        422 if validation fails (handled by FastAPI automatically)
        400 if the GitHub repo cannot be fetched
    """
    from services.github_client import github_client
    from services.issue_finder.enricher import enrich_issue
    import re
    import uuid as uuid_module

    # Parse owner and repo from the GitHub URL
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/?$", body.github_repo_url)
    if not match:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Invalid GitHub repo URL", "code": "INVALID_REPO_URL"},
        )

    owner, repo_name = match.group(1), match.group(2)

    # Fetch or create the project record
    project = (
        db.query(Project)
        .filter(Project.github_owner == owner, Project.github_repo == repo_name)
        .first()
    )

    if not project:
        repo_data = github_client.get_repo(owner, repo_name)
        if not repo_data:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "Could not fetch GitHub repo info", "code": "REPO_NOT_FOUND"},
            )
        project = Project(
            name=repo_data.get("full_name", f"{owner}/{repo_name}"),
            github_url=repo_data.get("html_url", body.github_repo_url),
            github_owner=owner,
            github_repo=repo_name,
            description=repo_data.get("description") or "",
            website_url=repo_data.get("homepage") or None,
            avatar_url=repo_data.get("owner", {}).get("avatar_url", ""),
            social_links={"github": f"https://github.com/{owner}/{repo_name}"},
            activity_score=0,
            activity_status="active",
        )
        db.add(project)
        db.flush()  # Get the project ID before creating the task

    # Enrich the description (applies AI if description is short)
    issue_dict = {
        "body": body.description,
        "github_owner": owner,
        "github_repo": repo_name,
        "github_issue_number": None,
        "title": body.title,
        "labels": [],
    }
    enriched = enrich_issue(issue_dict, repo_description=project.description or "")

    # If the maintainer specified a paid amount, record it as a label so
    # contributors can see the bounty value on the card (e.g. "$50 bounty").
    task_labels: list[str] = []
    if body.is_paid and body.paid_amount:
        task_labels.append(body.paid_amount)

    task = Task(
        project_id=project.id,
        title=body.title,
        description_original=body.description,
        description_display=enriched["description_display"],
        is_ai_generated=enriched["is_ai_generated"],
        labels=task_labels,
        contribution_type=body.contribution_type,
        is_paid=body.is_paid,
        difficulty=body.difficulty,
        source="manual_post",
        github_issue_url=body.github_issue_url or f"https://github.com/{owner}/{repo_name}",
        # New user submissions go into the moderation queue — never live immediately.
        # An admin must approve before is_active=True and review_status='approved'.
        is_active=False,
        review_status="pending_review",
        # submitter_email is stored for admin follow-up only — never in public responses.
        # Validated as a real email address by the EmailStr schema field.
        submitter_email=body.submitter_email,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info("Manual task created", extra={"task_id": str(task.id), "owner": owner, "repo": repo_name})

    return {
        "success": True,
        "data": {
            "id": str(task.id),
            "message": "Your task is live on Nocos.",
        },
    }
