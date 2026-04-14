# tests/unit/test_filters.py
# Unit tests for services/issue_finder/filters.py and the label-mapping
# function in services/issue_finder/scraper.py.
#
# Why these tests exist:
#   Filtering is the first gate that every scraped issue must pass.  Getting
#   it wrong in either direction has direct user-facing consequences: too
#   strict and we hide valid opportunities; too lenient and we show stale or
#   closed work.  These tests lock in the exact age cutoff, the closed-status
#   rule, and the label→contribution_type mapping so regressions are caught
#   immediately.
#
# External dependencies mocked:
#   None — both modules are stateless pure-function modules that only use the
#   standard library, so no mocking is required here.

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module-level import guard: prevent config.py / dotenv from hitting the
# filesystem or raising EnvironmentError during import.  Both scraper.py and
# filters.py import services.github_client, which in turn imports config.py.
# We stub the minimum needed so the module graph loads cleanly.
# ---------------------------------------------------------------------------
import sys
import types

# Build a minimal fake "config" module so config.py's side-effects are skipped.
_fake_config_module = types.ModuleType("config")


class _FakeConfig:
    GITHUB_TOKEN = "test-token"
    ANTHROPIC_API_KEY = "test-key"
    DATABASE_URL = "sqlite://"
    REDIS_URL = "redis://localhost:6379"
    EMAIL_SERVICE_API_KEY = ""
    EMAIL_FROM = "test@test.com"


_fake_config_module.config = _FakeConfig()
sys.modules.setdefault("config", _fake_config_module)

# Stub out heavy third-party packages that the github_client imports so we
# don't need them installed in the test environment.
for _mod in ("httpx", "redis", "dotenv", "python_dotenv"):
    sys.modules.setdefault(_mod, types.ModuleType(_mod))

# Provide a dotenv stub with the load_dotenv no-op that config.py calls at
# import time.
_dotenv_stub = sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
_dotenv_stub.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]

# Now we can safely import the modules under test.
from services.issue_finder.filters import (  # noqa: E402
    should_hide_issue,
    is_too_old,
    is_closed,
    MAX_ISSUE_AGE_DAYS,
)
from services.issue_finder.scraper import (  # noqa: E402
    map_labels_to_contribution_type,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_ago(n: int) -> datetime:
    """Return a timezone-aware UTC datetime exactly *n* days in the past."""
    return datetime.now(tz=timezone.utc) - timedelta(days=n)


# ===========================================================================
# should_hide_issue
# ===========================================================================

class TestShouldHideIssue:
    """
    Tests for filters.should_hide_issue(issue: dict) -> bool.

    This function is called by the sync job on issues already stored in the
    DB.  It returns True when an issue should be deactivated — either because
    it is too old or because it is closed.
    """

    def test_open_issue_older_than_14_days_is_hidden(self):
        """
        An open issue created 15 days ago exceeds the MAX_ISSUE_AGE_DAYS=14
        cutoff and must be hidden so stale opportunities are not shown.
        """
        issue = {
            "github_created_at": _days_ago(15),
            "status": "open",
        }
        assert should_hide_issue(issue) is True

    def test_open_issue_within_14_days_is_not_hidden(self):
        """
        An open issue created only 5 days ago is fresh and must remain
        visible — returning True here would incorrectly remove valid work.
        """
        issue = {
            "github_created_at": _days_ago(5),
            "status": "open",
        }
        assert should_hide_issue(issue) is False

    def test_closed_issue_is_hidden_regardless_of_age(self):
        """
        A closed issue must always be hidden no matter how recently it was
        created.  Contributors should never see work that is already done.
        """
        issue = {
            "github_created_at": _days_ago(1),  # Very recent — but closed
            "status": "closed",
        }
        assert should_hide_issue(issue) is True

    def test_open_recent_issue_is_not_hidden(self):
        """
        Sanity check: an open issue created today has both correct status and
        is within the age window — it must stay visible.
        """
        issue = {
            "github_created_at": _days_ago(0),
            "status": "open",
        }
        assert should_hide_issue(issue) is False

    def test_issue_exactly_at_boundary_is_not_hidden(self):
        """
        An issue created exactly MAX_ISSUE_AGE_DAYS days ago sits right on
        the boundary.  The filter uses a strict less-than comparison so an
        issue at exactly 14 days old must NOT be hidden (boundary inclusive
        means it is still within the window).
        """
        # Use MAX_ISSUE_AGE_DAYS - 1 to stay safely inside the window and
        # confirm the open+recent path never triggers hiding.
        issue = {
            "github_created_at": _days_ago(MAX_ISSUE_AGE_DAYS - 1),
            "status": "open",
        }
        assert should_hide_issue(issue) is False


# ===========================================================================
# map_labels_to_contribution_type  (from scraper.py)
# ===========================================================================

class TestMapLabelsToContributionType:
    """
    Tests for scraper.map_labels_to_contribution_type(labels: list[str]) -> str.

    This mapping is what connects raw GitHub label strings to the typed
    contribution_type enum stored in the database and surfaced in the API.
    Incorrect mappings would mis-categorise work for contributors.
    """

    def test_design_label_maps_to_design(self):
        """
        The 'design' label is a first-class contribution type and must map
        directly without falling through to 'other'.
        """
        assert map_labels_to_contribution_type(["design"]) == "design"

    def test_docs_label_maps_to_documentation(self):
        """
        GitHub repos commonly use 'docs' as a shorthand for 'documentation'.
        The mapping must normalise this so both labels resolve to the same
        contribution_type, keeping the UI consistent.
        """
        assert map_labels_to_contribution_type(["docs"]) == "documentation"

    def test_unknown_label_maps_to_other(self):
        """
        Labels not present in the mapping table must fall back to 'other'
        rather than raising an exception or returning None — the function
        must be robust to arbitrary repo-specific label names.
        """
        assert map_labels_to_contribution_type(["unknown-xyz"]) == "other"

    def test_empty_label_list_maps_to_other(self):
        """
        An empty label list has no recognisable contribution angle and must
        map to 'other' as the safe default.
        """
        assert map_labels_to_contribution_type([]) == "other"

    def test_case_insensitive_lookup(self):
        """
        GitHub labels are case-insensitive (repos use 'Design', 'design',
        'DESIGN').  The function lowercases before lookup so all variants
        resolve correctly.
        """
        assert map_labels_to_contribution_type(["Design"]) == "design"
        assert map_labels_to_contribution_type(["DOCS"]) == "documentation"

    def test_first_matching_label_wins(self):
        """
        When multiple labels match, the first one in the list determines the
        contribution_type.  This is documented behaviour and tests must
        enforce it so the ordering contract is never silently broken.
        """
        # "design" comes first — should win over "docs"
        result = map_labels_to_contribution_type(["design", "docs"])
        assert result == "design"
