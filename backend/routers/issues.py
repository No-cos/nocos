# routers/issues.py
# REST API endpoints for issue (task) discovery and manual submission.
# All queries filter by is_active=True so hidden/stale/closed issues
# never appear in any response.

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from db import get_db
from models.task import Task
from models.project import Project
from schemas.issue import IssueCreateRequest

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
        "description_display": task.description_display,
        "is_ai_generated": task.is_ai_generated,
        "labels": task.labels or [],
        "contribution_type": task.contribution_type,
        "is_paid": task.is_paid,
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
    query = (
        db.query(Task)
        .join(Task.project)
        .options(joinedload(Task.project))
        .filter(Task.is_active == True)
        .filter(Project.is_active == True)
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

    # Apply pagination and sort by most recent
    tasks = (
        query
        .order_by(Task.created_at.desc())
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

    task = (
        db.query(Task)
        .options(joinedload(Task.project))
        .filter(Task.id == uid, Task.is_active == True)
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

    return {"success": True, "data": issue_data}


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

    task = Task(
        project_id=project.id,
        title=body.title,
        description_original=body.description,
        description_display=enriched["description_display"],
        is_ai_generated=enriched["is_ai_generated"],
        labels=[],
        contribution_type=body.contribution_type,
        is_paid=body.is_paid,
        difficulty=body.difficulty,
        source="manual_post",
        github_issue_url=body.github_issue_url or f"https://github.com/{owner}/{repo_name}",
        is_active=True,
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
