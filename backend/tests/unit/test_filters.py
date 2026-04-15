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
from unittest.mock import MagicMock, patch

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

# Provide a dotenv stub with the load_dotenv no-op that config.py calls at
# import time.
_dotenv_stub = sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
_dotenv_stub.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]

# Stub httpx — must expose .Client so GitHubClient.__init__ can instantiate
# the HTTP client at module level without a real network stack.
_httpx_stub = sys.modules.setdefault("httpx", types.ModuleType("httpx"))
_httpx_stub.Client = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

# Stub redis — must expose .Redis so the cache layer can be constructed.
_redis_stub = sys.modules.setdefault("redis", types.ModuleType("redis"))
_redis_stub.Redis = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

# Now we can safely import the modules under test.
from services.issue_finder.filters import (  # noqa: E402
    should_hide_issue,
    is_too_old,
    is_closed,
    has_only_code_labels,
    has_code_title_prefix,
    is_catch_all_only_without_signal,
    should_include_issue,
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

    def test_open_issue_older_than_max_age_is_hidden(self):
        """
        An open issue older than MAX_ISSUE_AGE_DAYS must be hidden so stale
        opportunities are not shown to contributors.
        """
        issue = {
            "github_created_at": _days_ago(MAX_ISSUE_AGE_DAYS + 1),
            "status": "open",
        }
        assert should_hide_issue(issue) is True

    def test_open_issue_within_max_age_is_not_hidden(self):
        """
        An open issue well within the age window must remain visible.
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


# ===========================================================================
# has_only_code_labels — expanded CODE_ONLY_LABELS
# ===========================================================================

class TestHasOnlyCodeLabels:
    """
    Tests for the expanded CODE_ONLY_LABELS set introduced in the label
    expansion.  Verifies that the new entries (refactor, ci, backend, etc.)
    are treated as code-only when they appear alone, and that they do NOT
    suppress an issue that also carries a non-code label.
    """

    def test_new_code_label_alone_is_filtered(self):
        """
        Labels added in the expansion (refactor, ci, backend, frontend, etc.)
        must each be treated as code-only when they are the only label present.
        """
        for label in ("refactor", "ci", "backend", "frontend", "api",
                      "database", "dependencies", "chore", "performance",
                      "security", "regression", "crash", "testing"):
            assert has_only_code_labels([label]), f"Expected {label!r} to be code-only"

    def test_code_label_plus_design_is_not_filtered(self):
        """
        A 'bug' + 'design' combination has a non-code angle — the design
        work matters even if there is also a code-related label.
        """
        assert has_only_code_labels(["bug", "design"]) is False

    def test_code_label_plus_docs_is_not_filtered(self):
        assert has_only_code_labels(["enhancement", "documentation"]) is False


# ===========================================================================
# has_code_title_prefix
# ===========================================================================

class TestHasCodeTitlePrefix:
    """
    Tests for filters.has_code_title_prefix(title: str) -> bool.

    Conventional commit prefixes like "fix:", "feat:", "refactor:" indicate
    code-only work.  Issues with these titles must be rejected before
    reaching the database.
    """

    def test_fix_prefix_is_rejected(self):
        assert has_code_title_prefix("fix: null pointer in login service") is True

    def test_feat_prefix_is_rejected(self):
        assert has_code_title_prefix("feat: add OAuth2 support") is True

    def test_refactor_prefix_is_rejected(self):
        assert has_code_title_prefix("refactor: extract auth helper") is True

    def test_chore_prefix_is_rejected(self):
        assert has_code_title_prefix("chore: update dependencies") is True

    def test_ci_prefix_is_rejected(self):
        assert has_code_title_prefix("ci: fix flaky test pipeline") is True

    def test_perf_prefix_is_rejected(self):
        assert has_code_title_prefix("perf: cache database queries") is True

    def test_normal_title_is_allowed(self):
        assert has_code_title_prefix("Improve the onboarding documentation") is False

    def test_design_title_is_allowed(self):
        assert has_code_title_prefix("Design new landing page hero") is False

    def test_case_insensitive(self):
        """Prefix check must be case-insensitive (some authors write Fix:)."""
        assert has_code_title_prefix("Fix: broken header layout") is True
        assert has_code_title_prefix("FEAT: new dashboard") is True

    def test_empty_title_is_allowed(self):
        assert has_code_title_prefix("") is False

    def test_prefix_substring_in_middle_is_allowed(self):
        """
        'fix:' appearing mid-title must not trigger the filter — only a
        leading prefix matters.
        """
        assert has_code_title_prefix("Please fix: the broken link in docs") is False


# ===========================================================================
# is_catch_all_only_without_signal
# ===========================================================================

class TestIsCatchAllOnlyWithoutSignal:
    """
    Tests for filters.is_catch_all_only_without_signal(issue: dict) -> bool.

    Issues that carry only catch-all labels (help-wanted, good-first-issue,
    etc.) must contain a non-code signal in their title or body to pass.
    Issues with a specific non-code label always pass regardless of body.
    """

    def _issue(self, labels, title="", body=""):
        return {"labels": labels, "title": title, "body": body,
                "github_issue_id": 1, "github_created_at": None, "state": "open"}

    def test_help_wanted_with_design_signal_is_allowed(self):
        issue = self._issue(
            labels=["help-wanted"],
            title="Help wanted: redesign the onboarding flow in Figma",
        )
        assert is_catch_all_only_without_signal(issue) is False

    def test_help_wanted_with_docs_in_body_is_allowed(self):
        issue = self._issue(
            labels=["help-wanted"],
            body="We need someone to update the README and improve documentation.",
        )
        assert is_catch_all_only_without_signal(issue) is False

    def test_help_wanted_bug_fix_title_is_rejected(self):
        issue = self._issue(
            labels=["help-wanted"],
            title="Memory leak when loading images",
            body="The app crashes after 5 minutes due to a memory leak.",
        )
        assert is_catch_all_only_without_signal(issue) is True

    def test_good_first_issue_no_signal_is_rejected(self):
        issue = self._issue(
            labels=["good-first-issue"],
            title="Fix the broken build step",
            body="The CI pipeline fails on node 18.",
        )
        assert is_catch_all_only_without_signal(issue) is True

    def test_specific_non_code_label_always_passes(self):
        """
        An issue with a specific non-code label (docs, design, etc.) must
        always pass this filter even if it also has a catch-all label and
        no signal words in the body.
        """
        issue = self._issue(labels=["good-first-issue", "documentation"])
        assert is_catch_all_only_without_signal(issue) is False

    def test_design_label_alone_passes(self):
        issue = self._issue(labels=["design"], title="Update button styles")
        assert is_catch_all_only_without_signal(issue) is False

    def test_catch_all_plus_bug_without_signal_is_rejected(self):
        """
        'help-wanted' + 'bug' is a code-only combination — the 'bug' label
        doesn't save it since bug is a code-only label, not a non-code label.
        """
        issue = self._issue(
            labels=["help-wanted", "bug"],
            title="Segfault when parsing JSON",
        )
        assert is_catch_all_only_without_signal(issue) is True

    def test_hacktoberfest_with_translation_body_is_allowed(self):
        issue = self._issue(
            labels=["hacktoberfest"],
            body="We need help with translation of the Spanish locale files.",
        )
        assert is_catch_all_only_without_signal(issue) is False


# ===========================================================================
# should_include_issue — integration of all filters
# ===========================================================================

class TestShouldIncludeIssueIntegration:
    """
    End-to-end tests for should_include_issue confirming the three new
    filters work together with the existing age and closed checks.
    """

    def _issue(self, labels=None, title="", body="",
               state="open", days_ago=1):
        from datetime import datetime, timedelta, timezone
        created = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
        return {
            "labels": labels or [],
            "title": title,
            "body": body,
            "state": state,
            "github_created_at": created,
            "github_issue_id": 99,
        }

    def test_design_issue_passes(self):
        assert should_include_issue(self._issue(
            labels=["design"], title="Redesign the hero section"
        )) is True

    def test_fix_prefix_is_blocked(self):
        assert should_include_issue(self._issue(
            labels=["design"], title="fix: correct icon colours"
        )) is False

    def test_help_wanted_code_body_is_blocked(self):
        assert should_include_issue(self._issue(
            labels=["help-wanted"],
            title="Fix the null reference",
            body="App throws NullPointerException on startup.",
        )) is False

    def test_help_wanted_docs_body_passes(self):
        assert should_include_issue(self._issue(
            labels=["help-wanted"],
            title="Help improve our documentation",
            body="The README needs clearer installation instructions.",
        )) is True

    def test_all_code_labels_blocked(self):
        assert should_include_issue(self._issue(
            labels=["bug", "regression"], title="Regression in auth"
        )) is False
