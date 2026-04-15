# tests/unit/test_scraper.py
# Unit tests for services/issue_finder/scraper.py.
#
# Why these tests exist:
#   The scraper is the entry point for all GitHub data entering Nocos.  Two
#   correctness properties are critical:
#     1. Pull requests must be silently dropped — GitHub's issues endpoint
#        returns PRs mixed in with issues and they must never reach the DB.
#     2. Deduplication — the same issue can appear under multiple label
#        queries.  Storing duplicates would show contributors the same task
#        multiple times and corrupt analytics.
#   These tests verify both properties by replacing all GitHub API calls with
#   controlled in-memory fakes.
#
# External dependencies mocked:
#   - services.github_client.github_client.get_issues_by_label  (GitHub API)
#   - services.issue_finder.scraper.build_project_data           (GitHub API)
#   - services.issue_finder.scraper.scrape_issues_for_label      (GitHub API)
#   No real network calls are made.

import sys
import types
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Bootstrap stubs (same pattern as other test files)
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

_dotenv = sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
_dotenv.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]

# Stub httpx — must expose .Client so GitHubClient.__init__ can instantiate
# the HTTP client at module level without a real network stack.
_httpx_stub = sys.modules.setdefault("httpx", types.ModuleType("httpx"))
_httpx_stub.Client = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

# Stub redis — must expose .Redis so the cache layer can be constructed.
_redis_stub = sys.modules.setdefault("redis", types.ModuleType("redis"))
_redis_stub.Redis = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

# Import the module under test after stubs are in place.
from services.issue_finder.scraper import (  # noqa: E402
    map_labels_to_contribution_type,
    scrape_issues_for_label,
    scrape_repo,
    build_project_data,
    NON_CODE_LABELS,
    OPEN_SOURCE_LICENSES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw_issue(issue_id: int, title: str = "Test issue", labels: list | None = None) -> dict:
    """
    Return a minimal raw GitHub API issue dict (no 'pull_request' key).
    """
    return {
        "id": issue_id,
        "number": issue_id,
        "title": title,
        "body": "Some body text here.",
        "state": "open",
        "html_url": f"https://github.com/owner/repo/issues/{issue_id}",
        "created_at": "2026-04-10T10:00:00Z",
        "comments_url": "",
        "labels": [{"name": lbl} for lbl in (labels or [])],
    }


def _raw_pr(pr_id: int) -> dict:
    """
    Return a minimal raw GitHub API item that represents a pull request.
    GitHub marks PRs by including a 'pull_request' key in the response.
    """
    item = _raw_issue(pr_id, title="A pull request")
    item["pull_request"] = {"url": "https://api.github.com/repos/owner/repo/pulls/1"}
    return item


def _structured_issue(issue_id: int) -> dict:
    """
    Return a minimal structured issue dict as would be returned by
    scrape_issues_for_label — used to mock that function for scrape_repo tests.
    """
    return {
        "github_issue_id": issue_id,
        "github_issue_number": issue_id,
        "title": f"Issue {issue_id}",
        "body": "Body text.",
        "labels": ["design"],
        "contribution_type": "design",
        "github_issue_url": f"https://github.com/owner/repo/issues/{issue_id}",
        "github_created_at": None,
        "state": "open",
        "comments_url": "",
        "github_owner": "owner",
        "github_repo": "repo",
    }


_VALID_PROJECT = {
    "name": "owner/repo",
    "github_url": "https://github.com/owner/repo",
    "github_owner": "owner",
    "github_repo": "repo",
    "description": "A test repository",
    "website_url": None,
    "avatar_url": "",
    "social_links": {},
    "last_commit_date": None,
    "is_archived": False,
}


# ===========================================================================
# map_labels_to_contribution_type — additional mappings
# ===========================================================================

class TestMapLabelsAdditionalMappings:
    """
    Additional mapping tests for scraper.map_labels_to_contribution_type.

    test_filters.py already covers 'design', 'docs', and unknown labels.
    This class covers the less-obvious mappings that are equally important
    for correct filtering and display in the UI.
    """

    def test_pr_review_label_maps_to_pr_review(self):
        """
        'pr-review' is a first-class contribution type in Nocos.  The hyphen
        must be preserved in the label lookup and produce the underscore form
        expected by the DB enum.
        """
        assert map_labels_to_contribution_type(["pr-review"]) == "pr_review"

    def test_data_label_maps_to_data_analytics(self):
        """
        GitHub repos use 'data' as a broad label; Nocos maps it to the more
        descriptive 'data_analytics' enum value so contributors understand
        the contribution type at a glance.
        """
        assert map_labels_to_contribution_type(["data"]) == "data_analytics"

    def test_empty_list_maps_to_other(self):
        """
        An issue with no labels has no discernible contribution type and must
        fall back to 'other' — this must never raise an IndexError or return
        None.
        """
        assert map_labels_to_contribution_type([]) == "other"

    def test_good_first_issue_maps_to_other(self):
        """
        'good-first-issue' is a GitHub meta-label that says nothing about
        contribution type; it must resolve to 'other'.
        """
        assert map_labels_to_contribution_type(["good-first-issue"]) == "other"

    def test_translation_label_maps_to_translation(self):
        """
        'translation' is its own contribution type — verify it maps directly
        rather than falling through to 'other'.
        """
        assert map_labels_to_contribution_type(["translation"]) == "translation"

    def test_new_design_labels_map_to_design(self):
        """New labels added in the expansion must resolve to the correct type."""
        for label in ("needs-design", "figma", "ui/ux", "design-needed", "visual"):
            assert map_labels_to_contribution_type([label]) == "design", label

    def test_new_documentation_labels_map_correctly(self):
        for label in ("needs-docs", "improve-docs", "technical-writing", "writing"):
            assert map_labels_to_contribution_type([label]) == "documentation", label

    def test_new_translation_labels_map_correctly(self):
        for label in ("i18n", "l10n", "localization", "needs-translation", "language"):
            assert map_labels_to_contribution_type([label]) == "translation", label

    def test_new_community_labels_map_correctly(self):
        for label in ("outreach", "devrel", "developer-relations", "advocacy"):
            assert map_labels_to_contribution_type([label]) == "community", label

    def test_social_media_labels_map_to_social_media(self):
        for label in ("social-media", "twitter", "announcement"):
            assert map_labels_to_contribution_type([label]) == "social_media", label

    def test_project_management_labels_map_correctly(self):
        for label in ("project-management", "planning", "roadmap", "triage", "needs-triage"):
            assert map_labels_to_contribution_type([label]) == "project_management", label

    def test_pr_review_variants_map_correctly(self):
        for label in ("needs-review", "review-needed", "review-requested"):
            assert map_labels_to_contribution_type([label]) == "pr_review", label

    def test_analytics_labels_map_to_data_analytics(self):
        for label in ("analytics", "metrics", "tracking", "data-analysis"):
            assert map_labels_to_contribution_type([label]) == "data_analytics", label

    def test_catch_all_labels_map_to_other(self):
        """Catch-all labels have no specific type — they resolve to 'other'."""
        for label in ("help-wanted", "first-timers-only", "up-for-grabs",
                      "contributions-welcome", "beginner-friendly", "low-hanging-fruit"):
            assert map_labels_to_contribution_type([label]) == "other", label


# ===========================================================================
# scrape_issues_for_label — PR filtering
# ===========================================================================

class TestScrapeIssuesForLabelPrFiltering:
    """
    Tests for scraper.scrape_issues_for_label(owner, repo, label).

    GitHub's Issues API returns both issues and pull requests in the same
    response.  PRs must be dropped before the data reaches any downstream
    processing.  Storing a PR as a task would confuse contributors and
    break the data model assumptions.
    """

    @patch("services.issue_finder.scraper.github_client")
    def test_pull_requests_are_filtered_out(self, mock_gc):
        """
        When the raw GitHub response contains one real issue and one pull
        request, only the issue must appear in the result.  The PR must be
        silently dropped (no exception, no logging required by this contract).
        """
        mock_gc.get_issues_by_label.return_value = [
            _raw_issue(issue_id=101, labels=["design"]),
            _raw_pr(pr_id=102),
        ]

        result = scrape_issues_for_label("owner", "repo", "design")

        assert len(result) == 1
        assert result[0]["github_issue_id"] == 101

    @patch("services.issue_finder.scraper.github_client")
    def test_all_prs_returns_empty_list(self, mock_gc):
        """
        If every item in the GitHub response is a PR, the result must be an
        empty list — not None, not an exception.
        """
        mock_gc.get_issues_by_label.return_value = [
            _raw_pr(1),
            _raw_pr(2),
            _raw_pr(3),
        ]

        result = scrape_issues_for_label("owner", "repo", "docs")

        assert result == []

    @patch("services.issue_finder.scraper.github_client")
    def test_all_real_issues_all_returned(self, mock_gc):
        """
        When there are no PRs in the response, every issue must be present
        in the output — the filter must not over-eagerly drop real items.
        """
        mock_gc.get_issues_by_label.return_value = [
            _raw_issue(10, labels=["design"]),
            _raw_issue(11, labels=["design"]),
        ]

        result = scrape_issues_for_label("owner", "repo", "design")

        assert len(result) == 2
        assert {r["github_issue_id"] for r in result} == {10, 11}

    @patch("services.issue_finder.scraper.github_client")
    def test_returned_issue_has_required_fields(self, mock_gc):
        """
        Each structured issue dict returned by scrape_issues_for_label must
        include all fields expected by downstream modules (enricher, filters,
        DB writer).  Missing fields would cause KeyError exceptions later.
        """
        mock_gc.get_issues_by_label.return_value = [
            _raw_issue(200, labels=["docs"])
        ]

        result = scrape_issues_for_label("owner", "repo", "docs")

        assert len(result) == 1
        issue = result[0]
        required_fields = {
            "github_issue_id",
            "github_issue_number",
            "title",
            "body",
            "labels",
            "contribution_type",
            "github_issue_url",
            "github_created_at",
            "state",
            "github_owner",
            "github_repo",
        }
        for field in required_fields:
            assert field in issue, f"Missing field: {field}"


# ===========================================================================
# scrape_repo — deduplication
# ===========================================================================

class TestScrapeRepoDeduplication:
    """
    Tests for scraper.scrape_repo(owner, repo_name).

    scrape_repo iterates over all NON_CODE_LABELS and calls
    scrape_issues_for_label for each.  An issue with two matching labels
    (e.g. both 'design' and 'ux') would appear in both calls.  The function
    must deduplicate by github_issue_id so each issue is stored exactly once.
    """

    @patch("services.issue_finder.scraper.scrape_issues_for_label")
    @patch("services.issue_finder.scraper.build_project_data")
    def test_duplicate_issue_from_two_labels_appears_once(
        self, mock_build, mock_scrape
    ):
        """
        When the same issue (same github_issue_id) is returned for two
        different label queries, it must appear exactly once in the final
        issues list.  Duplicates in the DB would surface the same task twice
        on the platform and break unique-constraint inserts.
        """
        mock_build.return_value = _VALID_PROJECT

        shared_issue = _structured_issue(issue_id=42)

        # Both calls return the same issue
        mock_scrape.return_value = [shared_issue]

        _, issues = scrape_repo("owner", "repo")

        assert len(issues) == 1
        assert issues[0]["github_issue_id"] == 42

    @patch("services.issue_finder.scraper.scrape_issues_for_label")
    @patch("services.issue_finder.scraper.build_project_data")
    def test_distinct_issues_from_different_labels_all_present(
        self, mock_build, mock_scrape
    ):
        """
        Distinct issues (different github_issue_ids) discovered under different
        labels must all appear in the result — deduplication must never drop
        genuinely unique issues.
        """
        mock_build.return_value = _VALID_PROJECT

        issues_by_label = {
            "design": [_structured_issue(1)],
            "docs": [_structured_issue(2)],
        }

        def _side_effect(owner, repo, label, **kwargs):
            return issues_by_label.get(label, [])

        mock_scrape.side_effect = _side_effect

        _, issues = scrape_repo("owner", "repo")

        ids_found = {i["github_issue_id"] for i in issues}
        assert 1 in ids_found
        assert 2 in ids_found

    @patch("services.issue_finder.scraper.scrape_issues_for_label")
    @patch("services.issue_finder.scraper.build_project_data")
    def test_returns_none_project_when_build_fails(
        self, mock_build, mock_scrape
    ):
        """
        If build_project_data returns None (e.g. the GitHub API is down for
        this repo), scrape_repo must return (None, []) and not attempt any
        label queries — there is no project to attach issues to.
        """
        mock_build.return_value = None

        project_data, issues = scrape_repo("owner", "missing-repo")

        assert project_data is None
        assert issues == []
        mock_scrape.assert_not_called()

    @patch("services.issue_finder.scraper.scrape_issues_for_label")
    @patch("services.issue_finder.scraper.build_project_data")
    def test_project_data_is_returned_alongside_issues(
        self, mock_build, mock_scrape
    ):
        """
        scrape_repo returns a 2-tuple of (project_data, issues).  The
        project_data dict must be the same object returned by build_project_data
        so the caller can upsert both in a single transaction.
        """
        mock_build.return_value = _VALID_PROJECT
        mock_scrape.return_value = []

        project_data, _ = scrape_repo("owner", "repo")

        assert project_data is _VALID_PROJECT


# ===========================================================================
# build_project_data — open source licence enforcement
# ===========================================================================

def _repo_data(
    *,
    spdx_id: str | None = "MIT",
    private: bool = False,
    archived: bool = False,
) -> dict:
    """
    Build a minimal GitHub repo API response dict for licence-check tests.
    """
    return {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "description": "Test repo",
        "homepage": None,
        "owner": {"avatar_url": ""},
        "private": private,
        "archived": archived,
        "license": {"spdx_id": spdx_id} if spdx_id else None,
    }


class TestBuildProjectDataLicenceEnforcement:
    """
    Tests for the open source licence gate in build_project_data().

    Every project ingested into Nocos must have a recognised SPDX licence.
    Private and archived repos are also rejected before any issue scraping
    begins — there is no point fetching labels for repos contributors cannot
    legally or practically contribute to.
    """

    @patch("services.issue_finder.scraper.github_client")
    def test_mit_licence_is_accepted(self, mock_gc):
        """
        MIT is the most common open source licence — it must pass the gate
        so Nocos can index the vast majority of GitHub projects.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id="MIT")
        mock_gc.get_last_commit_date.return_value = None

        result = build_project_data("owner", "repo")

        assert result is not None

    @patch("services.issue_finder.scraper.github_client")
    def test_apache_licence_is_accepted(self, mock_gc):
        mock_gc.get_repo.return_value = _repo_data(spdx_id="Apache-2.0")
        mock_gc.get_last_commit_date.return_value = None

        assert build_project_data("owner", "repo") is not None

    @patch("services.issue_finder.scraper.github_client")
    def test_null_licence_is_rejected(self, mock_gc):
        """
        A repo with no licence field (null) is all-rights-reserved by default.
        Contributors cannot legally submit code so it must be skipped.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id=None)

        assert build_project_data("owner", "repo") is None

    @patch("services.issue_finder.scraper.github_client")
    def test_noassertion_licence_is_rejected(self, mock_gc):
        """
        NOASSERTION means GitHub detected a file but could not identify the
        licence. The legal status is unknown — must be rejected to protect
        contributors from inadvertently working on proprietary code.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id="NOASSERTION")

        assert build_project_data("owner", "repo") is None

    @patch("services.issue_finder.scraper.github_client")
    def test_unknown_proprietary_licence_is_rejected(self, mock_gc):
        """
        An SPDX ID that is not in the allowlist (e.g. a custom or proprietary
        identifier) must be rejected — the allowlist is the gate, not a
        blocklist of known bad values.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id="Proprietary-1.0")

        assert build_project_data("owner", "repo") is None

    @patch("services.issue_finder.scraper.github_client")
    def test_private_repo_is_rejected(self, mock_gc):
        """
        Private repos cannot be contributed to by the public — they must
        be skipped regardless of licence.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id="MIT", private=True)

        assert build_project_data("owner", "repo") is None

    @patch("services.issue_finder.scraper.github_client")
    def test_archived_repo_is_rejected(self, mock_gc):
        """
        Archived repos are frozen — GitHub disables issue creation and
        pull requests. No point showing contributors tasks they cannot submit.
        """
        mock_gc.get_repo.return_value = _repo_data(spdx_id="MIT", archived=True)

        assert build_project_data("owner", "repo") is None

    @patch("services.issue_finder.scraper.github_client")
    def test_all_allowlisted_licences_are_accepted(self, mock_gc):
        """
        Every licence in OPEN_SOURCE_LICENSES must pass the gate individually.
        This prevents future edits that accidentally add a licence string that
        does not match the comparison logic.
        """
        mock_gc.get_last_commit_date.return_value = None

        for spdx in OPEN_SOURCE_LICENSES:
            mock_gc.get_repo.return_value = _repo_data(spdx_id=spdx)
            result = build_project_data("owner", "repo")
            assert result is not None, f"Licence {spdx!r} should be accepted"
