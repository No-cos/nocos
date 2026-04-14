# routers/projects.py
# REST API endpoint for project details.
# Returns the full project object including social links, activity status,
# and website URL — used by the "About This Project" section on the detail page.

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


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
