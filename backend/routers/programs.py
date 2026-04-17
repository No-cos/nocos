# routers/programs.py
# Public and admin REST endpoints for paid stipend programs.
#
# Public endpoints (no auth):
#   GET  /api/v1/programs          — list all active programs, filterable by status
#   GET  /api/v1/programs/:id      — single program detail
#
# Admin endpoints (Bearer token required, same as admin.py):
#   POST   /api/v1/admin/programs        — create a program
#   PUT    /api/v1/admin/programs/:id    — update a program
#   DELETE /api/v1/admin/programs/:id    — soft-delete (is_active=False)

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from config import config
from db import get_db
from models.program import Program

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/programs", tags=["programs"])
admin_router = APIRouter(prefix="/admin/programs", tags=["admin"])


# ─── Serialiser ───────────────────────────────────────────────────────────────

def _program_to_dict(program: Program) -> dict:
    """Serialise a Program ORM object to the API response shape."""
    return {
        "id": str(program.id),
        "name": program.name,
        "organisation": program.organisation,
        "logo_url": program.logo_url,
        "description": program.description,
        "stipend_range": program.stipend_range,
        "application_open": program.application_open.isoformat() if program.application_open else None,
        "application_deadline": program.application_deadline.isoformat() if program.application_deadline else None,
        "program_start": program.program_start.isoformat() if program.program_start else None,
        "tags": program.tags or [],
        "application_url": program.application_url,
        "status": program.status,
        "is_active": program.is_active,
        "created_at": program.created_at.isoformat(),
        "updated_at": program.updated_at.isoformat(),
    }


# ─── Public endpoints ─────────────────────────────────────────────────────────

@router.get("")
def list_programs(
    status: Optional[str] = Query(
        None,
        description="Filter by status: upcoming | open | closed",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    List all active programs with an optional status filter.

    Programs are ordered: open first, then upcoming, then closed — so the
    most actionable programs always appear at the top regardless of creation order.

    Returns:
        Envelope: { success, data: [Program], meta: { total } }
    """
    query = db.query(Program).filter(Program.is_active == True)

    if status and status in ("upcoming", "open", "closed"):
        query = query.filter(Program.status == status)

    # Sort: open → upcoming → closed, then by application_deadline ascending
    # so the soonest deadlines surface first within each status group.
    from sqlalchemy import case
    status_order = case(
        (Program.status == "open", 0),
        (Program.status == "upcoming", 1),
        (Program.status == "closed", 2),
        else_=3,
    )
    programs = (
        query
        .order_by(status_order, Program.application_deadline.asc().nullslast())
        .all()
    )

    return {
        "success": True,
        "data": [_program_to_dict(p) for p in programs],
        "meta": {"total": len(programs)},
    }


@router.get("/{program_id}")
def get_program(program_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Get a single active program by ID.

    Returns:
        Envelope: { success, data: Program }

    Raises:
        404 if the program does not exist or is not active
    """
    try:
        uid = UUID(program_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Program not found")

    program = (
        db.query(Program)
        .filter(Program.id == uid, Program.is_active == True)
        .first()
    )
    if not program:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Program not found", "code": "PROGRAM_NOT_FOUND"},
        )

    return {"success": True, "data": _program_to_dict(program)}


# ─── Admin auth helper (mirrors admin.py) ─────────────────────────────────────

def _check_admin(request: Request) -> None:
    token = config.ADMIN_SECRET_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="Admin access is not configured")
    if request.headers.get("Authorization", "") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorised")


# ─── Admin Pydantic schemas ───────────────────────────────────────────────────

class ProgramCreateBody(BaseModel):
    name: str
    organisation: str
    logo_url: Optional[str] = None
    description: str
    stipend_range: str
    application_open: Optional[date] = None
    application_deadline: Optional[date] = None
    program_start: Optional[date] = None
    tags: list[str] = []
    application_url: str
    status: str = "upcoming"  # upcoming | open | closed


class ProgramUpdateBody(BaseModel):
    name: Optional[str] = None
    organisation: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    stipend_range: Optional[str] = None
    application_open: Optional[date] = None
    application_deadline: Optional[date] = None
    program_start: Optional[date] = None
    tags: Optional[list[str]] = None
    application_url: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@admin_router.post("", include_in_schema=False)
def create_program(
    body: ProgramCreateBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Create a new program. Requires admin bearer token."""
    _check_admin(request)

    if body.status not in ("upcoming", "open", "closed"):
        raise HTTPException(status_code=422, detail="status must be upcoming, open, or closed")

    program = Program(
        name=body.name,
        organisation=body.organisation,
        logo_url=body.logo_url,
        description=body.description,
        stipend_range=body.stipend_range,
        application_open=body.application_open,
        application_deadline=body.application_deadline,
        program_start=body.program_start,
        tags=body.tags,
        application_url=body.application_url,
        status=body.status,
        is_active=True,
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    logger.info("Program created by admin", extra={"program_id": str(program.id), "name": program.name})
    return {"success": True, "data": _program_to_dict(program)}


@admin_router.put("/{program_id}", include_in_schema=False)
def update_program(
    program_id: str,
    body: ProgramUpdateBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Update an existing program. Requires admin bearer token."""
    _check_admin(request)

    try:
        uid = UUID(program_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Program not found")

    program = db.query(Program).filter(Program.id == uid).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    if body.status is not None and body.status not in ("upcoming", "open", "closed"):
        raise HTTPException(status_code=422, detail="status must be upcoming, open, or closed")

    # Apply only the fields that were explicitly provided
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)

    db.commit()
    db.refresh(program)

    logger.info("Program updated by admin", extra={"program_id": program_id})
    return {"success": True, "data": _program_to_dict(program)}


@admin_router.delete("/{program_id}", include_in_schema=False)
def delete_program(
    program_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Soft-delete a program by setting is_active=False.
    The row is kept in the database for audit purposes.
    Requires admin bearer token.
    """
    _check_admin(request)

    try:
        uid = UUID(program_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Program not found")

    program = db.query(Program).filter(Program.id == uid).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    program.is_active = False
    db.commit()

    logger.info("Program soft-deleted by admin", extra={"program_id": program_id})
    return {"success": True, "id": program_id}


@admin_router.get("", include_in_schema=False)
def list_all_programs(request: Request, db: Session = Depends(get_db)) -> dict:
    """List all programs including inactive ones. Admin only."""
    _check_admin(request)

    programs = db.query(Program).order_by(Program.created_at.desc()).all()
    return {
        "success": True,
        "count": len(programs),
        "data": [_program_to_dict(p) for p in programs],
    }
