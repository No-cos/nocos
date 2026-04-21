# schemas/ai_tasks.py
# Pydantic schemas for the AI Task Generator endpoints.
# /api/v1/generate-tasks/preview  — generate tasks without saving to DB
# /api/v1/generate-tasks/publish  — save previously generated tasks to DB

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re


class GenerateTasksPreviewRequest(BaseModel):
    """
    Request body for the preview endpoint.

    The repo_url is validated to be a syntactically correct GitHub repo URL
    before any network calls are made.
    """
    repo_url: str = Field(
        ...,
        description="Full GitHub repository URL (e.g. https://github.com/owner/repo)",
    )

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Reject URLs that are not valid GitHub repo URLs."""
        v = v.strip().rstrip("/")
        if not re.match(r"^https://github\.com/[^/]+/[^/]+$", v):
            raise ValueError(
                "repo_url must be a valid GitHub repository URL "
                "(e.g. https://github.com/owner/repo)"
            )
        return v


class GeneratedTaskItem(BaseModel):
    """
    A single AI-generated task as returned from Claude.

    Used in both the preview response (to show the user) and the publish
    request (the user sends these back to be saved).
    """
    title: str = Field(..., max_length=300, description="Action-oriented task title")
    description: str = Field(..., description="2-sentence contributor-facing description")
    category: Literal[
        "design", "documentation", "translation",
        "community", "marketing", "research"
    ] = Field(..., description="Contribution type")
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_hours: Literal[3, 6, 10]


class GenerateTasksPreviewResponse(BaseModel):
    """
    Response from the preview endpoint.

    Returns the 6 generated tasks and the resolved repo name so the frontend
    can display a heading like "Tasks for django/django" without a second call.
    """
    success: bool = True
    data: dict  # { repo_name: str, tasks: list[GeneratedTaskItem] }


class GenerateTasksPublishRequest(BaseModel):
    """
    Request body for the publish endpoint.

    The client sends back the tasks from the preview response (possibly with
    modifications). The server validates and saves them to the database.
    """
    repo_url: str = Field(
        ...,
        description="The same GitHub repo URL used in the preview request",
    )
    tasks: list[GeneratedTaskItem] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Task list from the preview response — up to 10 tasks",
    )

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not re.match(r"^https://github\.com/[^/]+/[^/]+$", v):
            raise ValueError(
                "repo_url must be a valid GitHub repository URL"
            )
        return v


class GenerateTasksPublishResponse(BaseModel):
    """Response from the publish endpoint."""
    success: bool = True
    data: dict  # { saved_count: int, tasks: list[{id, title}] }
