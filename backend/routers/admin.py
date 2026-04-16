# routers/admin.py
# Admin endpoints for content moderation of user-submitted tasks.
# All endpoints are protected by a bearer token and hidden from public docs.
#
# Usage (replace YOUR_TOKEN and TASK_ID with real values):
#
#   List pending tasks:
#   curl -H "Authorization: Bearer YOUR_TOKEN" \
#        https://nocos-production.up.railway.app/api/v1/admin/pending
#
#   Approve a task:
#   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
#        https://nocos-production.up.railway.app/api/v1/admin/approve/TASK_ID
#
#   Reject a task:
#   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
#        https://nocos-production.up.railway.app/api/v1/admin/reject/TASK_ID
#
#   Moderation stats:
#   curl -H "Authorization: Bearer YOUR_TOKEN" \
#        https://nocos-production.up.railway.app/api/v1/admin/stats

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from config import config
from db import get_db
from models.task import Task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_admin(request: Request) -> None:
    """
    Validate the Authorization: Bearer <token> header against ADMIN_SECRET_TOKEN.

    Raises 503 if the token is not configured (never leave endpoints open).
    Raises 401 on missing or wrong token.
    Never logs the token value.
    """
    token = config.ADMIN_SECRET_TOKEN
    if not token:
        logger.warning("Admin endpoint called but ADMIN_SECRET_TOKEN is not set — rejecting")
        raise HTTPException(status_code=503, detail="Admin access is not configured")

    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorised")


@router.get("/pending", include_in_schema=False)
def list_pending(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Return all tasks currently in pending_review state.
    Includes basic project info so the reviewer has context.
    """
    _check_admin(request)

    tasks = (
        db.query(Task)
        .options(joinedload(Task.project))
        .filter(Task.review_status == "pending_review")
        .order_by(Task.created_at.asc())
        .all()
    )

    return {
        "success": True,
        "count": len(tasks),
        "data": [
            {
                "id": str(t.id),
                "title": t.title,
                "contribution_type": t.contribution_type,
                "is_paid": t.is_paid,
                "difficulty": t.difficulty,
                "github_issue_url": t.github_issue_url,
                "description_display": t.description_display,
                "created_at": t.created_at.isoformat(),
                "project": {
                    "id": str(t.project.id),
                    "name": t.project.name,
                    "github_owner": t.project.github_owner,
                    "github_repo": t.project.github_repo,
                },
            }
            for t in tasks
        ],
    }


@router.post("/approve/{task_id}", include_in_schema=False)
def approve_task(task_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Approve a pending task — set review_status='approved' and is_active=True
    so it becomes visible in the discovery grid.
    """
    _check_admin(request)

    try:
        uid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    task = db.query(Task).filter(Task.id == uid).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.review_status = "approved"
    task.is_active = True
    db.commit()

    logger.info("Task approved by admin", extra={"task_id": task_id})
    return {"success": True, "id": task_id, "review_status": "approved"}


@router.post("/reject/{task_id}", include_in_schema=False)
def reject_task(task_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Reject a pending task — set review_status='rejected' and ensure is_active=False
    so it never appears publicly.
    """
    _check_admin(request)

    try:
        uid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    task = db.query(Task).filter(Task.id == uid).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.review_status = "rejected"
    task.is_active = False
    db.commit()

    logger.info("Task rejected by admin", extra={"task_id": task_id})
    return {"success": True, "id": task_id, "review_status": "rejected"}


@router.get("/stats", include_in_schema=False)
def moderation_stats(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Return counts of tasks in each review state.
    """
    _check_admin(request)

    rows = (
        db.query(Task.review_status, func.count(Task.id))
        .group_by(Task.review_status)
        .all()
    )

    counts = {status: count for status, count in rows}
    return {
        "success": True,
        "pending_review": counts.get("pending_review", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
    }
