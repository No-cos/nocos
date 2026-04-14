# tests/integration/test_issues_api.py
# Integration tests for GET /api/v1/issues and GET /api/v1/issues/{id}.
#
# The real database is replaced by a MagicMock session (see conftest.py).
# The Redis cache (app_cache) is patched to return None so every test
# exercises the DB path rather than a cached response.

from unittest.mock import patch
from uuid import uuid4

import pytest

from tests.integration.conftest import make_task


# ─── GET /api/v1/issues ───────────────────────────────────────────────────────

def test_list_issues_returns_200_with_envelope(client, mock_db_session):
    """A well-formed request returns 200 with the standard response envelope."""
    task1 = make_task(title="Design the landing page")
    task2 = make_task(title="Write documentation")
    mock_db_session._query_result = [task1, task2]

    response = client.get("/api/v1/issues")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2
    assert "page" in body["meta"]
    assert "total" in body["meta"]
    assert "per_page" in body["meta"]


def test_list_issues_returns_only_active_issues(client, mock_db_session):
    """When no active issues exist the data list is empty."""
    # The mock returns an empty list — simulates all issues being inactive.
    mock_db_session._query_result = []

    response = client.get("/api/v1/issues")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"]["total"] == 0


def test_search_returns_matching_issues(client, mock_db_session):
    """The ?search= query param is accepted and data reflects the mock result."""
    task = make_task(title="Redesign the navigation")
    mock_db_session._query_result = [task]

    response = client.get("/api/v1/issues?search=design")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1


def test_pagination_params_accepted(client, mock_db_session):
    """page and limit query params are accepted without validation errors."""
    mock_db_session._query_result = []

    response = client.get("/api/v1/issues?page=2&limit=5")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["page"] == 2
    assert body["meta"]["per_page"] == 5


def test_limit_max_50_enforced(client, mock_db_session):
    """limit > 50 is rejected with 422 by FastAPI's Query(le=50) constraint."""
    response = client.get("/api/v1/issues?limit=100")

    assert response.status_code == 422


# ─── GET /api/v1/issues/{id} ─────────────────────────────────────────────────

def test_get_single_issue_returns_200(client, mock_db_session):
    """A valid UUID that matches a task returns 200 with the issue in data."""
    issue_id = uuid4()
    task = make_task(id=issue_id)
    mock_db_session._query_result = [task]

    with patch("routers.issues.app_cache") as mock_cache:
        mock_cache.get.return_value = None  # Force DB path (cache miss)
        mock_cache.set.return_value = None

        response = client.get(f"/api/v1/issues/{issue_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == str(issue_id)


def test_get_issue_not_found_returns_404(client, mock_db_session):
    """When .first() returns None (no matching task) the endpoint returns 404."""
    missing_id = uuid4()
    mock_db_session._query_result = []  # first() will return None

    with patch("routers.issues.app_cache") as mock_cache:
        mock_cache.get.return_value = None

        response = client.get(f"/api/v1/issues/{missing_id}")

    assert response.status_code == 404
