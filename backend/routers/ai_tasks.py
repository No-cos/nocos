# routers/ai_tasks.py
# AI Task Generator endpoints.
#
# POST /api/v1/generate-tasks/preview
#   Analyse a GitHub repo and return AI-generated non-code tasks WITHOUT saving.
#   Rate limit: 5 requests per IP per hour.
#
# POST /api/v1/generate-tasks/publish
#   Save the previously previewed tasks to the database.
#   Rate limit: 3 publishes per IP per hour.
#
# No authentication required — these are public endpoints.
# All rate limiting is in-memory (resets on restart). For a production
# deployment with multiple processes, replace with Redis-based counters.

import logging
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db import get_db
from schemas.ai_tasks import (
    GenerateTasksPreviewRequest,
    GenerateTasksPublishRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate-tasks", tags=["ai-tasks"])

# ── In-memory rate limiting ───────────────────────────────────────────────────
# Structure: { "preview": { ip: [timestamp, ...] }, "publish": { ... } }
_rate_limit_store: dict[str, dict[str, list[float]]] = {
    "preview": defaultdict(list),
    "publish": defaultdict(list),
}

# Rate limit configuration: (max_requests, window_seconds)
_RATE_LIMITS = {
    "preview": (5, 3600),   # 5 requests per IP per hour
    "publish": (3, 3600),   # 3 publishes per IP per hour
}


def _check_rate_limit(action: str, ip: str) -> None:
    """
    Raise HTTP 429 if the IP has exceeded the rate limit for the given action.

    Sliding window: entries older than the window are pruned on each check
    so the log never grows unbounded.

    Args:
        action: "preview" or "publish"
        ip:     Client IP address string

    Raises:
        HTTPException 429 if the rate limit is exceeded.
    """
    max_requests, window = _RATE_LIMITS[action]
    now = time.time()
    log = _rate_limit_store[action][ip]

    # Prune entries outside the current window
    _rate_limit_store[action][ip] = [t for t in log if now - t < window]
    current = _rate_limit_store[action][ip]

    if len(current) >= max_requests:
        retry_after = int(window - (now - current[0]))
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": f"Rate limit exceeded. You may make up to {max_requests} "
                         f"{action} requests per hour. Try again in {retry_after} seconds.",
                "code": "RATE_LIMIT_EXCEEDED",
                "retry_after_seconds": max(retry_after, 0),
            },
        )

    _rate_limit_store[action][ip].append(now)


def _client_ip(request: Request) -> str:
    """
    Extract the real client IP from the request.

    Respects X-Forwarded-For set by Railway's reverse proxy.
    Falls back to the direct client IP.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First entry in the chain is the originating client
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/preview")
def preview_tasks(
    body: GenerateTasksPreviewRequest,
    request: Request,
) -> dict:
    """
    Analyse a GitHub repository and return AI-generated non-code tasks.

    Nothing is saved to the database.  The response contains the generated tasks
    and the resolved repo name — the client can display them for review and then
    POST to /publish to save selected tasks.

    Rate limit: 5 requests per IP per hour.

    Request body:
        repo_url: Full GitHub URL (e.g. https://github.com/django/django)

    Returns:
        { success, data: { repo_name, tasks: [...] } }

    Error codes:
        400 INVALID_REPO       — repo is private, archived, or unlicensed
        400 MISSING_README     — README not found (required for generation)
        429 RATE_LIMIT_EXCEEDED— too many requests from this IP
        503 GENERATION_FAILED  — Claude could not produce valid tasks
    """
    from services.ai_task_generator import preview_tasks_for_repo

    ip = _client_ip(request)
    _check_rate_limit("preview", ip)

    logger.info(
        "AI task preview requested",
        extra={"repo_url": body.repo_url, "ip": ip},
    )

    try:
        result = preview_tasks_for_repo(body.repo_url)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": str(e),
                "code": "INVALID_REPO",
            },
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": str(e),
                "code": "GENERATION_FAILED",
            },
        )
    except Exception:
        logger.exception("Unexpected error in AI task preview")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "An unexpected error occurred. Please try again.",
                "code": "INTERNAL_ERROR",
            },
        )

    logger.info(
        "AI task preview complete",
        extra={
            "repo_url": body.repo_url,
            "repo_name": result.get("repo_name"),
            "task_count": len(result.get("tasks", [])),
        },
    )

    return {"success": True, "data": result}


@router.post("/publish")
def publish_tasks(
    body: GenerateTasksPublishRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Save AI-generated tasks to the database after the user reviews them.

    Only called when the user explicitly clicks Publish.  Tasks are saved
    with source='ai_generated', is_active=True, and review_status='approved'
    so they appear immediately on the discovery grid.

    Rate limit: 3 publishes per IP per hour.

    Request body:
        repo_url: The GitHub repo URL (same as used in the preview request)
        tasks:    List of task dicts from the preview response (1–10 tasks)

    Returns:
        { success, data: { saved_count, tasks: [{id, title}] } }

    Error codes:
        400 INVALID_REPO       — repo URL is malformed or repo cannot be fetched
        429 RATE_LIMIT_EXCEEDED— too many publishes from this IP
        500 INTERNAL_ERROR     — unexpected failure during DB write
    """
    from services.ai_task_generator import publish_tasks_for_repo

    ip = _client_ip(request)
    _check_rate_limit("publish", ip)

    logger.info(
        "AI task publish requested",
        extra={"repo_url": body.repo_url, "task_count": len(body.tasks), "ip": ip},
    )

    # Convert Pydantic models to plain dicts for the service layer
    tasks_as_dicts = [task.model_dump() for task in body.tasks]

    try:
        result = publish_tasks_for_repo(
            tasks=tasks_as_dicts,
            repo_url=body.repo_url,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": str(e),
                "code": "INVALID_REPO",
            },
        )
    except Exception:
        logger.exception("Unexpected error in AI task publish")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to save tasks. Please try again.",
                "code": "INTERNAL_ERROR",
            },
        )

    logger.info(
        "AI task publish complete",
        extra={
            "repo_url": body.repo_url,
            "saved_count": result.get("saved_count", 0),
        },
    )

    return {"success": True, "data": result}
