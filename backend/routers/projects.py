# routers/projects.py
# REST API endpoints for project details and the maintainer preview helper.
# Returns project info used by the "About This Project" section on the detail
# page, and by the Post a Task form to auto-fill project info on blur.

import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db
from models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

# Regex that matches the GitHub repo URL pattern required by SKILLS.md §16
_GITHUB_REPO_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")

# Redis TTL for the preview endpoint — 1 hour, matching project cache strategy
_PREVIEW_TTL = 3600


@router.get("/preview")
def preview_project(
    url: str = Query(..., description="Full GitHub repo URL to preview"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return lightweight project info (name, avatar, description) for a GitHub URL.

    Used by the Post a Task form to auto-fill project details when the
    maintainer pastes a repo URL and moves focus away from the field.

    Strategy:
      1. Validate URL matches https://github.com/<owner>/<repo> pattern.
      2. Check if the project already exists in our DB (fastest path).
      3. If not found locally, fetch from GitHub API via github_client.get_repo()
         which already handles caching (TTL 1 hour) and rate limit safety.

    Args:
        url: Full GitHub repo URL (e.g. https://github.com/chaoss/augur)

    Returns:
        Envelope: { success, data: { name, avatar_url, description } }

    Raises:
        422 if the URL doesn't match the expected pattern
        404 if the repo cannot be found on GitHub
    """
    from services.github_client import github_client

    # Validate URL pattern before making any external calls
    match = _GITHUB_REPO_RE.match(url.strip())
    if not match:
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "error": "Invalid GitHub repo URL. Expected: https://github.com/<owner>/<repo>",
                "code": "INVALID_REPO_URL",
            },
        )

    owner, repo_name = match.group(1), match.group(2)

    # Fast path: check if this project is already in our database
    existing = (
        db.query(Project)
        .filter(
            Project.github_owner == owner,
            Project.github_repo == repo_name,
            Project.is_active == True,
        )
        .first()
    )
    if existing:
        logger.info(
            "Project preview served from DB",
            extra={"owner": owner, "repo": repo_name},
        )
        return {
            "success": True,
            "data": {
                "name": existing.name,
                "avatar_url": existing.avatar_url,
                "description": existing.description or "",
            },
        }

    # Slow path: fetch from GitHub API (github_client caches for 1 hour)
    repo_data = github_client.get_repo(owner, repo_name)
    if not repo_data:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": "Couldn't find this repo. Check the URL and try again.",
                "code": "REPO_NOT_FOUND",
            },
        )

    logger.info(
        "Project preview fetched from GitHub",
        extra={"owner": owner, "repo": repo_name},
    )
    return {
        "success": True,
        "data": {
            "name": repo_data.get("name") or f"{owner}/{repo_name}",
            "avatar_url": repo_data.get("owner", {}).get("avatar_url", ""),
            "description": repo_data.get("description") or "",
        },
    }


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Get a single active project's details including social links and activity.

    Used by the task detail page "About This Project" section.
    Social links are returned as-is — the frontend renders only the keys
    that have non-null values (SKILLS.md Section 13).

    Args:
        project_id: UUID of the project

    Returns:
        Envelope: { success, data: ProjectResponse }

    Raises:
        404 if the project does not exist or is not active
    """
    try:
        uid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")

    project = (
        db.query(Project)
        .filter(Project.id == uid, Project.is_active == True)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": "Project not found",
                "code": "PROJECT_NOT_FOUND",
            },
        )

    return {
        "success": True,
        "data": {
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
            "last_commit_date": (
                project.last_commit_date.isoformat()
                if project.last_commit_date
                else None
            ),
            "is_active": project.is_active,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        },
    }
