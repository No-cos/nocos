# routers/projects.py
# API endpoints for project information.
# Phase 1: Returns stub responses. Full implementation in Phase 2.
# TODO: Connect to database queries after Phase 2 — see models/project.py

from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict:
    """
    Get a single project's details including social links and activity status.

    Used by the task detail page "About This Project" section.
    Social links are rendered conditionally — only shown if the data exists.
    """
    # Phase 1 stub — full implementation in Phase 2
    return {
        "success": False,
        "error": "Not implemented yet",
        "code": "NOT_IMPLEMENTED",
    }
