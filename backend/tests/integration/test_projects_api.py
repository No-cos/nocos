# tests/integration/test_projects_api.py
# Integration tests for GET /api/v1/projects/{id} and GET /api/v1/projects/preview.
#
# The real database is replaced by a MagicMock session (see conftest.py).
# GitHub API calls are patched at the services layer so no network traffic
# is produced.

from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

from tests.integration.conftest import make_project


# ─── GET /api/v1/projects/{project_id} ───────────────────────────────────────

def test_get_project_returns_200(client, mock_db_session):
    """A valid UUID that matches an active project returns 200 with project data."""
    project_id = uuid4()
    project = make_project(id=project_id, name="Nocos")
    mock_db_session._query_result = [project]

    response = client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Nocos"
    assert body["data"]["id"] == str(project_id)


def test_get_project_not_found_returns_404(client, mock_db_session):
    """When no project matches the UUID the endpoint returns 404."""
    mock_db_session._query_result = []  # first() will return None

    response = client.get(f"/api/v1/projects/{uuid4()}")

    assert response.status_code == 404


def test_get_project_invalid_uuid_returns_404(client, mock_db_session):
    """A path segment that is not a valid UUID is caught and returns 404."""
    response = client.get("/api/v1/projects/not-a-uuid")

    assert response.status_code == 404


# ─── GET /api/v1/projects/preview ─────────────────────────────────────────────

def test_preview_valid_url_returns_project_data(client, mock_db_session):
    """
    A valid GitHub URL whose repo is not in the DB is fetched from the
    GitHub API and the essential fields are returned in the envelope.
    """
    # DB has no matching project — mock returns empty list so first() is None.
    mock_db_session._query_result = []

    mock_repo = {
        "name": "augur",
        "description": "Measuring the health of open source communities.",
        "owner": {"avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4"},
    }

    with patch("routers.projects.github_client") as mock_gc:
        mock_gc.get_repo.return_value = mock_repo

        response = client.get("/api/v1/projects/preview?url=https://github.com/chaoss/augur")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "name" in body["data"]
    assert "avatar_url" in body["data"]
    assert "description" in body["data"]
    assert body["data"]["name"] == "augur"


def test_preview_invalid_url_returns_422(client, mock_db_session):
    """A URL that does not match the github.com/<owner>/<repo> pattern returns 422."""
    response = client.get("/api/v1/projects/preview?url=not-a-github-url")

    assert response.status_code == 422


def test_preview_repo_not_found_returns_404(client, mock_db_session):
    """When github_client.get_repo returns an empty dict the endpoint returns 404."""
    mock_db_session._query_result = []

    with patch("routers.projects.github_client") as mock_gc:
        # An empty dict is falsy — the router treats this as "repo not found".
        mock_gc.get_repo.return_value = {}

        response = client.get("/api/v1/projects/preview?url=https://github.com/owner/repo")

    assert response.status_code == 404
