# tests/unit/test_sync.py
# Unit tests for services/sync.py.
#
# Why these tests exist:
#   The sync job runs every 6 hours and modifies live database rows.  An error
#   in the activity-status thresholds would mis-classify projects (showing an
#   inactive project as active, or vice versa) across the entire platform.  An
#   error in the archived-repo handler could leave tasks visible even when the
#   upstream project no longer exists.  These tests lock in:
#     1. The exact day-count boundaries for active / slow / inactive.
#     2. That archiving a repo deactivates the project AND all its tasks with
#        the correct hidden_reason.
#
# External dependencies mocked:
#   - services.github_client.github_client.get_repo  (GitHub API)
#   - services.cache.app_cache                        (Redis)
#   - SQLAlchemy Session and ORM objects              (PostgreSQL)
#   No real network or database calls are made.

import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap stubs
# ---------------------------------------------------------------------------

_fake_config_mod = sys.modules.get("config") or types.ModuleType("config")


class _FakeConfig:
    GITHUB_TOKEN = "test-token"
    ANTHROPIC_API_KEY = "test-key"
    DATABASE_URL = "sqlite://"
    REDIS_URL = "redis://localhost:6379"
    EMAIL_SERVICE_API_KEY = ""
    EMAIL_FROM = "test@test.com"


_fake_config_mod.config = _FakeConfig()  # type: ignore[attr-defined]
sys.modules.setdefault("config", _fake_config_mod)

for _name in ("httpx", "redis", "anthropic", "apscheduler",
              "apscheduler.schedulers", "apscheduler.schedulers.background"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

# apscheduler.schedulers.background.BackgroundScheduler is referenced at
# module level in sync.py — provide a minimal stub.
_bg_mod = sys.modules["apscheduler.schedulers.background"]
_bg_mod.BackgroundScheduler = MagicMock  # type: ignore[attr-defined]

_dotenv = sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
_dotenv.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]

# Stub sqlalchemy so models can be imported without a real DB.
for _name in (
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.dialects",
    "sqlalchemy.dialects.postgresql",
    "sqlalchemy.sql",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_sqlalchemy = sys.modules["sqlalchemy"]
for _attr in ("Column", "Boolean", "DateTime", "Enum", "ForeignKey",
              "Integer", "String", "Text"):
    setattr(_sqlalchemy, _attr, MagicMock())

_sqlalchemy_orm = sys.modules["sqlalchemy.orm"]
_sqlalchemy_orm.relationship = MagicMock()  # type: ignore[attr-defined]

_sqlalchemy_dialects_pg = sys.modules["sqlalchemy.dialects.postgresql"]
_sqlalchemy_dialects_pg.ARRAY = MagicMock()  # type: ignore[attr-defined]
_sqlalchemy_dialects_pg.UUID = MagicMock()   # type: ignore[attr-defined]

_sqlalchemy_sql = sys.modules["sqlalchemy.sql"]
_sqlalchemy_sql.func = MagicMock()  # type: ignore[attr-defined]

# Stub models.base so models/task.py and models/project.py can be imported.
_models_base = types.ModuleType("models.base")
_models_base.Base = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("models.base", _models_base)
sys.modules.setdefault("models", types.ModuleType("models"))

# Stub services.cache so sync.py's `from services.cache import app_cache` works.
_cache_mod = types.ModuleType("services.cache")
_cache_mod.app_cache = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("services.cache", _cache_mod)

# Now import the module under test.
from services.sync import (  # noqa: E402
    calculate_activity_status,
    _sync_project,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_ago(n: int) -> datetime:
    """Return a timezone-aware UTC datetime exactly *n* days in the past."""
    return datetime.now(tz=timezone.utc) - timedelta(days=n)


def _make_mock_task(task_id: int = 1) -> MagicMock:
    """
    Return a MagicMock that satisfies the Task attribute contract used by
    _hide_task() and _sync_project():
      - id, is_active, hidden_reason, hidden_at
    """
    task = MagicMock()
    task.id = uuid.uuid4()
    task.is_active = True
    task.hidden_reason = None
    task.hidden_at = None
    return task


def _make_mock_project(owner: str = "owner", repo: str = "repo") -> MagicMock:
    """
    Return a MagicMock that satisfies the Project attribute contract used by
    _sync_project():
      - id, github_owner, github_repo, is_active, activity_status,
        activity_score, last_commit_date
    """
    project = MagicMock()
    project.id = uuid.uuid4()
    project.github_owner = owner
    project.github_repo = repo
    project.is_active = True
    project.activity_status = "active"
    project.activity_score = 90
    project.last_commit_date = None
    return project


# ===========================================================================
# calculate_activity_status
# ===========================================================================

class TestCalculateActivityStatus:
    """
    Tests for sync.calculate_activity_status(last_commit_date) -> (str, int).

    The three status tiers (active / slow / inactive) determine the badge
    shown on each project card.  An incorrect boundary would make a barely-
    active project appear inactive, or an inactive project appear active.
    """

    def test_commit_10_days_ago_is_active(self):
        """
        A commit 10 days ago is well within the 30-day active window.
        The returned status must be 'active' and the score must be in the
        active range (80–100).
        """
        status, score = calculate_activity_status(_days_ago(10))

        assert status == "active"
        assert 80 <= score <= 100

    def test_commit_30_days_ago_is_active(self):
        """
        A commit exactly 30 days ago is at the boundary of the active window.
        The spec says <= 30 days is active, so this must still be 'active'.
        """
        status, score = calculate_activity_status(_days_ago(30))

        assert status == "active"

    def test_commit_60_days_ago_is_slow(self):
        """
        A commit 60 days ago falls in the 30–90 day 'slow' band.  Projects
        in this range are maintained but not actively developed.
        """
        status, score = calculate_activity_status(_days_ago(60))

        assert status == "slow"
        assert 40 <= score <= 79

    def test_commit_90_days_ago_is_slow(self):
        """
        A commit exactly 90 days ago is at the boundary of the slow window.
        The spec says 30–90 days is slow (inclusive), so this must be 'slow'.
        """
        status, score = calculate_activity_status(_days_ago(90))

        assert status == "slow"

    def test_commit_120_days_ago_is_inactive(self):
        """
        A commit 120 days ago is 30 days past the 90-day cutoff and must be
        classified as 'inactive'.  Showing such a project as 'slow' would
        mislead contributors about the project's health.
        """
        status, score = calculate_activity_status(_days_ago(120))

        assert status == "inactive"
        assert 0 <= score <= 39

    def test_none_commit_date_is_inactive_zero_score(self):
        """
        When there is no commit date (new or data-missing project), the
        function must return exactly ('inactive', 0) — a safe default that
        does not inflate the project's apparent health.
        """
        status, score = calculate_activity_status(None)

        assert status == "inactive"
        assert score == 0

    def test_naive_datetime_is_handled(self):
        """
        Some data sources return timezone-naive datetimes.  The function
        must treat them as UTC rather than raising a TypeError, so stale
        data does not crash the sync job.
        """
        naive_dt = datetime.utcnow() - timedelta(days=5)  # no tzinfo
        status, score = calculate_activity_status(naive_dt)

        assert status == "active"

    def test_score_decreases_with_age(self):
        """
        Within the same status tier, older commits should yield lower scores.
        This is a monotonicity check: score(5 days) >= score(20 days).
        """
        _, score_recent = calculate_activity_status(_days_ago(5))
        _, score_older = calculate_activity_status(_days_ago(20))

        assert score_recent >= score_older


# ===========================================================================
# _sync_project — archived repo
# ===========================================================================

class TestSyncProjectArchivedRepo:
    """
    Tests for sync._sync_project(project, session) when the GitHub repo is
    archived.

    When GitHub marks a repo as archived it means no further development is
    planned.  Nocos must:
      1. Set project.is_active = False.
      2. Set task.is_active = False and task.hidden_reason = 'archived' for
         every active task belonging to that project.
    Failing to do this would leave orphaned tasks visible on the platform
    pointing at a repo that will never accept contributions.
    """

    def _build_session_with_tasks(self, tasks: list) -> MagicMock:
        """
        Build a mock SQLAlchemy Session whose query().filter().all() chain
        returns *tasks*.
        """
        session = MagicMock()
        query_result = MagicMock()
        query_result.all.return_value = tasks
        filter_result = MagicMock()
        filter_result.all.return_value = tasks
        session.query.return_value.filter.return_value = filter_result
        return session

    @patch("services.sync.github_client")
    def test_archived_repo_sets_project_inactive(self, mock_gc):
        """
        After _sync_project is called for an archived repo, the project's
        is_active attribute must be False.  An active project pointing at an
        archived repo would surface a dead project in search results.
        """
        mock_gc.get_repo.return_value = {"archived": True}

        project = _make_mock_project()
        session = self._build_session_with_tasks([])

        _sync_project(project, session)

        assert project.is_active is False

    @patch("services.sync.github_client")
    def test_archived_repo_deactivates_all_tasks(self, mock_gc):
        """
        Every active task in the project must have is_active set to False
        after the archived-repo handler runs.  Tasks that remain active would
        be shown to contributors on a project that can no longer accept work.
        """
        mock_gc.get_repo.return_value = {"archived": True}

        task1 = _make_mock_task(1)
        task2 = _make_mock_task(2)
        project = _make_mock_project()
        session = self._build_session_with_tasks([task1, task2])

        _sync_project(project, session)

        assert task1.is_active is False
        assert task2.is_active is False

    @patch("services.sync.github_client")
    def test_archived_repo_sets_hidden_reason_archived(self, mock_gc):
        """
        The hidden_reason on each deactivated task must be exactly 'archived'
        so operators and analytics can distinguish archive-driven hiding from
        staleness or closure.
        """
        mock_gc.get_repo.return_value = {"archived": True}

        task1 = _make_mock_task(1)
        task2 = _make_mock_task(2)
        project = _make_mock_project()
        session = self._build_session_with_tasks([task1, task2])

        _sync_project(project, session)

        assert task1.hidden_reason == "archived"
        assert task2.hidden_reason == "archived"

    @patch("services.sync.github_client")
    def test_archived_repo_project_added_to_session(self, mock_gc):
        """
        The modified project object must be passed to session.add() so the
        is_active=False change is included in the transaction commit.  Without
        this call, the project change would be lost on the next session flush.
        """
        mock_gc.get_repo.return_value = {"archived": True}

        project = _make_mock_project()
        session = self._build_session_with_tasks([])

        _sync_project(project, session)

        session.add.assert_any_call(project)

    @patch("services.sync.github_client")
    def test_non_archived_repo_does_not_deactivate_project(self, mock_gc):
        """
        When the repo is NOT archived, the project's is_active must remain
        True (assuming no other change triggers deactivation).  This is a
        regression guard: the archived check must be conditional, not
        unconditional.
        """
        mock_gc.get_repo.return_value = {"archived": False}
        # Prevent the activity-score branch from failing on missing attributes.
        mock_gc.get_last_commit_date.return_value = None

        project = _make_mock_project()
        session = self._build_session_with_tasks([])

        _sync_project(project, session)

        assert project.is_active is True

    @patch("services.sync.github_client")
    def test_rate_limit_error_skips_sync_gracefully(self, mock_gc):
        """
        If github_client.get_repo raises RateLimitLowError, _sync_project must
        return without modifying the project.  The sync job must degrade
        gracefully when the API quota is exhausted, not crash.
        """
        from services.github_client import RateLimitLowError
        mock_gc.get_repo.side_effect = RateLimitLowError("rate limit")

        project = _make_mock_project()
        session = self._build_session_with_tasks([])

        # Must not raise
        _sync_project(project, session)

        # Project must be untouched
        assert project.is_active is True
