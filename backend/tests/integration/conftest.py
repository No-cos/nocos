# tests/integration/conftest.py
# Shared fixtures for all integration tests.
#
# Strategy: override FastAPI's get_db dependency with a MagicMock session so
# no real database connection is required. PostgreSQL-specific column types
# (UUID, ARRAY) make SQLite unsuitable as an in-process substitute.

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from db import get_db
from main import app


# ─── MockQuery ───────────────────────────────────────────────────────────────

class MockQuery:
    """
    Chainable query stub that mirrors the SQLAlchemy Query API.

    Tests control the return value by setting mock_db._query_result before
    making a request. .all() returns the list; .first() returns the first
    element or None; .count() returns len() of the list.
    """

    def __init__(self, result):
        self._result = result

    # All chaining methods return self so calls can be chained freely.
    def join(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._result)

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """
    A MagicMock that pretends to be an SQLAlchemy Session.

    The .query() method returns a MockQuery driven by ._query_result.
    Tests set mock_db_session._query_result = [...] before issuing requests.
    """
    mock = MagicMock()
    mock._query_result = []

    def _query(*args, **kwargs):
        return MockQuery(mock._query_result)

    mock.query.side_effect = _query
    # add / commit / refresh / close are fire-and-forget in tests
    mock.add.return_value = None
    mock.commit.return_value = None
    mock.refresh.return_value = None
    mock.close.return_value = None
    return mock


@pytest.fixture
def client(mock_db_session):
    """
    FastAPI TestClient with the real get_db dependency replaced by
    mock_db_session. Overrides are cleaned up after each test.
    """
    app.dependency_overrides[get_db] = lambda: mock_db_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ─── ORM object factories ─────────────────────────────────────────────────────

def make_project(**kwargs):
    """
    Return a MagicMock shaped like a Project ORM instance.

    All attributes have sensible defaults; pass keyword arguments to override
    specific fields for a given test.
    """
    now = datetime.now(tz=timezone.utc)
    project = MagicMock()
    project.id = kwargs.get("id", uuid4())
    project.name = kwargs.get("name", "Test Project")
    project.github_url = kwargs.get("github_url", "https://github.com/owner/repo")
    project.github_owner = kwargs.get("github_owner", "owner")
    project.github_repo = kwargs.get("github_repo", "repo")
    project.description = kwargs.get("description", "A test project")
    project.website_url = kwargs.get("website_url", None)
    project.avatar_url = kwargs.get("avatar_url", "https://avatars.githubusercontent.com/u/1?v=4")
    project.social_links = kwargs.get("social_links", {"github": "https://github.com/owner/repo"})
    project.activity_score = kwargs.get("activity_score", 42)
    project.activity_status = kwargs.get("activity_status", "active")
    project.last_commit_date = kwargs.get("last_commit_date", None)
    project.is_active = kwargs.get("is_active", True)
    project.created_at = kwargs.get("created_at", now)
    project.updated_at = kwargs.get("updated_at", now)
    return project


def make_task(**kwargs):
    """
    Return a MagicMock shaped like a Task ORM instance.

    Embeds a make_project() as the .project attribute unless overridden.
    All attributes have sensible defaults; pass keyword arguments to override.
    """
    now = datetime.now(tz=timezone.utc)
    task = MagicMock()
    task.id = kwargs.get("id", uuid4())
    task.project_id = kwargs.get("project_id", uuid4())
    task.project = kwargs.get("project", make_project())
    task.title = kwargs.get("title", "Fix a bug")
    task.description_display = kwargs.get("description_display", "Help fix this bug.")
    task.is_ai_generated = kwargs.get("is_ai_generated", False)
    task.labels = kwargs.get("labels", ["good first issue"])
    task.contribution_type = kwargs.get("contribution_type", "bug")
    task.is_paid = kwargs.get("is_paid", False)
    task.difficulty = kwargs.get("difficulty", "beginner")
    task.source = kwargs.get("source", "github")
    task.github_issue_url = kwargs.get("github_issue_url", "https://github.com/owner/repo/issues/1")
    task.github_created_at = kwargs.get("github_created_at", now)
    task.is_active = kwargs.get("is_active", True)
    task.created_at = kwargs.get("created_at", now)
    task.updated_at = kwargs.get("updated_at", now)
    return task
