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
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from config import config
from db import get_db
from models.subscriber import Subscriber
from models.task import Task
from services.email import send_approval_email, send_rejection_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class RejectBody(BaseModel):
    reason: str = "Your submission does not meet our contribution guidelines."


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
                "source": t.source,
                "github_issue_url": t.github_issue_url,
                "description_display": t.description_display,
                # submitter_email is only surfaced here in the protected admin endpoint.
                # It is intentionally absent from every public API response.
                "submitter_email": t.submitter_email,
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

    logger.info(
        "Task approved by admin",
        extra={"task_id": task_id, "has_email": bool(task.submitter_email)},
    )

    # Send approval email — failure must never block the approve response.
    if task.submitter_email:
        from services.email import _mask_email
        masked = _mask_email(task.submitter_email)
        try:
            task_url = f"{config.FRONTEND_URL}/tasks/{task.id}"
            logger.info(
                "Sending approval email",
                extra={"submitter": masked, "task_url": task_url},
            )
            sent = send_approval_email(task.submitter_email, task.title, task_url)
            logger.info(
                "Approval email send result",
                extra={"submitter": masked, "sent": sent},
            )
        except Exception:
            logger.error(
                "Unexpected error sending approval email",
                extra={"submitter": masked},
                exc_info=True,
            )
    else:
        logger.info("No submitter_email on task — approval email skipped", extra={"task_id": task_id})

    return {"success": True, "id": task_id, "review_status": "approved"}


@router.post("/reject/{task_id}", include_in_schema=False)
def reject_task(
    task_id: str,
    request: Request,
    body: RejectBody = RejectBody(),
    db: Session = Depends(get_db),
) -> dict:
    """
    Reject a pending task — set review_status='rejected' and ensure is_active=False
    so it never appears publicly. Sends a rejection email with the reason if a
    submitter_email is stored on the task.
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

    logger.info(
        "Task rejected by admin",
        extra={"task_id": task_id, "has_email": bool(task.submitter_email)},
    )

    # Send rejection email — failure must never block the reject response.
    if task.submitter_email:
        from services.email import _mask_email
        masked = _mask_email(task.submitter_email)
        try:
            logger.info(
                "Sending rejection email",
                extra={"submitter": masked, "reason": body.reason},
            )
            sent = send_rejection_email(task.submitter_email, task.title, body.reason)
            logger.info(
                "Rejection email send result",
                extra={"submitter": masked, "sent": sent},
            )
        except Exception:
            logger.error(
                "Unexpected error sending rejection email",
                extra={"submitter": masked},
                exc_info=True,
            )
    else:
        logger.info("No submitter_email on task — rejection email skipped", extra={"task_id": task_id})

    return {"success": True, "id": task_id, "review_status": "rejected"}


@router.delete("/tasks/{task_id}", include_in_schema=False)
def delete_task(task_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Permanently delete a task by ID.
    Protected by ADMIN_SECRET_TOKEN. Returns 404 if not found.
    """
    _check_admin(request)

    try:
        uid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    task = db.query(Task).filter(Task.id == uid).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        db.delete(task)
        db.commit()
        logger.info("Task deleted by admin", extra={"task_id": task_id})
        return {"success": True, "id": task_id}
    except Exception:
        db.rollback()
        logger.exception("Failed to delete task", extra={"task_id": task_id})
        raise HTTPException(status_code=500, detail="Failed to delete task")


@router.get("/tasks", include_in_schema=False)
def list_all_tasks(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Return all tasks (any status) for the admin management table.
    Ordered by created_at descending (newest first).
    """
    _check_admin(request)

    tasks = (
        db.query(Task)
        .options(joinedload(Task.project))
        .order_by(Task.created_at.desc())
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
                "review_status": t.review_status,
                "is_active": t.is_active,
                "source": t.source,
                "created_at": t.created_at.isoformat(),
                "project": {
                    "github_owner": t.project.github_owner,
                    "github_repo": t.project.github_repo,
                },
            }
            for t in tasks
        ],
    }


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

    confirmed_subscribers = (
        db.query(func.count(Subscriber.id))
        .filter(Subscriber.confirmed == True)
        .scalar()
    ) or 0

    return {
        "success": True,
        "pending_review": counts.get("pending_review", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "total_subscribers": confirmed_subscribers,
    }
