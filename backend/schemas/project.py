# schemas/project.py
# Pydantic response schemas for the Project model.
# These control exactly what the API returns — never expose internal fields
# (e.g. raw DB IDs, private notes) through schemas by accident.

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SocialLinks(BaseModel):
    """Social link URLs for a project. All fields except github are optional."""
    github: str
    twitter: Optional[str] = None
    discord: Optional[str] = None
    slack: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None


class ProjectResponse(BaseModel):
    """
    Public API representation of a project.

    Returned by GET /api/v1/projects/:id and embedded in issue responses.
    """
    id: UUID
    name: str
    github_url: str
    github_owner: str
    github_repo: str
    description: Optional[str]
    website_url: Optional[str]
    avatar_url: str
    social_links: SocialLinks
    activity_score: int
    activity_status: str
    last_commit_date: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    """
    Minimal project info embedded in issue card responses.
    Keeps the issue list payload small — full project data is fetched separately.
    """
    id: UUID
    name: str
    avatar_url: str
    activity_status: str
    github_owner: str
    github_repo: str

    model_config = {"from_attributes": True}
