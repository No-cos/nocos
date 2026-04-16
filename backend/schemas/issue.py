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

    Note: description_original is never exposed publicly — only description_display
    is returned in API responses (SKILLS.md §16). The raw description submitted here
    becomes description_original; description_display may be AI-enhanced.
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
    paid_amount: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional bounty/payment description (e.g. '$50 bounty'). "
                    "Stored as a label on the task so contributors can see it on the card.",
    )
    difficulty: Optional[str] = None
    github_issue_url: Optional[str] = None
    submitter_email: Optional[str] = Field(
        None,
        description="Contact email for the submitter — stored for moderation only, never returned publicly.",
    )


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
