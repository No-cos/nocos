# schemas/issue.py
# Pydantic request and response schemas for the Task (issue) model.
# Note: description_original is intentionally excluded from all response
# schemas — only description_display is ever returned publicly (SKILLS.md §16).

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from schemas.project import ProjectSummary


class IssueResponse(BaseModel):
    """
    Public API representation of a task for the discovery grid.

    Returned in paginated lists. Embeds a ProjectSummary so the card
    can render the project avatar and activity dot without a second request.
    """
    id: UUID
    project_id: UUID
    project: ProjectSummary
    title: str
    description_display: str
    is_ai_generated: bool
    labels: List[str]
    contribution_type: str
    is_paid: bool
    difficulty: Optional[str]
    source: str
    github_issue_url: str
    github_created_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueCreateRequest(BaseModel):
    """
    Request body for manually posting a task (maintainer submission).
    Validated by Pydantic before any business logic runs.
    """
    github_repo_url: str = Field(
        ...,
        description="Full GitHub repo URL — used to auto-fill project info",
        pattern=r"^https://github\.com/[^/]+/[^/]+$",
    )
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(
        ...,
        min_length=50,
        description="Plain-English description — what non-technical contributors will read",
    )
    contribution_type: str
    is_paid: bool = False
    difficulty: Optional[str] = None
    github_issue_url: Optional[str] = None


class IssueListMeta(BaseModel):
    """Pagination metadata included in list responses."""
    page: int
    total: int
    per_page: int


class IssueListResponse(BaseModel):
    """Envelope for paginated issue list responses."""
    success: bool = True
    data: List[IssueResponse]
    meta: IssueListMeta
