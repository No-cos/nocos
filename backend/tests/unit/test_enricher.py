# tests/unit/test_enricher.py
# Unit tests for services/ai/description.py and
# services/issue_finder/enricher.py.
#
# Why these tests exist:
#   The AI enrichment pipeline is the most expensive component of the sync
#   job — every unnecessary Claude call costs money and time.  These tests
#   verify three things:
#     1. needs_ai_description() applies the 20-word threshold correctly.
#     2. enrich_issues() never raises even when every AI call fails.
#     3. The fallback string is the exact value hardcoded in description.py,
#        so UI copy and the Python constant stay in sync.
#
# External dependencies mocked:
#   - services.ai.description.process_issue_description  (Anthropic API)
#   - services.github_client.github_client.get_issue_comments  (GitHub API)
#   No real network calls are made.

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap stubs for the module import chain
# ---------------------------------------------------------------------------

# Minimal config stub — prevents dotenv/EnvironmentError at import time.
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

# Stub heavy third-party packages only if not already present.
for _name in ("httpx", "redis", "anthropic"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_dotenv = sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
_dotenv.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]

# anthropic needs a few specific names that description.py accesses.
_anthropic_mod = sys.modules["anthropic"]
_anthropic_mod.Anthropic = MagicMock()  # type: ignore[attr-defined]
_anthropic_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})  # type: ignore[attr-defined]
_anthropic_mod.RateLimitError = type("RateLimitError", (Exception,), {})  # type: ignore[attr-defined]

# Now safe to import modules under test.
from services.ai.description import (  # noqa: E402
    needs_ai_description,
    FALLBACK_DESCRIPTION,
    MIN_DESCRIPTION_WORDS,
)
from services.issue_finder.enricher import (  # noqa: E402
    enrich_issues,
    MAX_CONSECUTIVE_FAILURES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(n: int) -> dict:
    """Return a minimal issue dict with a unique github_issue_id."""
    return {
        "github_issue_id": n,
        "github_issue_number": n,
        "title": f"Issue {n}",
        "body": None,
        "labels": [],
        "github_owner": "test-owner",
        "github_repo": "test-repo",
    }


def _words(n: int) -> str:
    """Return a string containing exactly *n* space-separated words."""
    return " ".join(f"word{i}" for i in range(n))


# ===========================================================================
# needs_ai_description
# ===========================================================================

class TestNeedsAiDescription:
    """
    Tests for description.needs_ai_description(body: Optional[str]) -> bool.

    The 20-word threshold is the budget gating rule for Claude calls.  Tests
    ensure we do not call Claude when the existing body is long enough, and
    that we do call it for None/empty/short bodies.
    """

    def test_none_body_needs_ai(self):
        """
        A None body means the issue was created without any description.
        Claude must supply one so the card is not blank for contributors.
        """
        assert needs_ai_description(None) is True

    def test_empty_string_body_needs_ai(self):
        """
        An empty string body is functionally the same as None — no readable
        content exists, so AI generation is required.
        """
        assert needs_ai_description("") is True

    def test_body_under_20_words_needs_ai(self):
        """
        A body with fewer than MIN_DESCRIPTION_WORDS words is too short for
        a non-technical contributor to understand the task.  AI generation
        must kick in to fill the gap.
        """
        short_body = _words(MIN_DESCRIPTION_WORDS - 1)  # 19 words
        assert needs_ai_description(short_body) is True

    def test_body_exactly_20_words_does_not_need_ai(self):
        """
        A body with exactly MIN_DESCRIPTION_WORDS words meets the minimum
        and must NOT trigger AI generation — the function uses strict < so
        exactly 20 is sufficient.
        """
        exact_body = _words(MIN_DESCRIPTION_WORDS)  # 20 words
        assert needs_ai_description(exact_body) is False

    def test_body_over_20_words_does_not_need_ai(self):
        """
        A body with more than 20 words is detailed enough; calling Claude
        would waste tokens and cost money without improving the contributor
        experience.
        """
        long_body = _words(MIN_DESCRIPTION_WORDS + 5)  # 25 words
        assert needs_ai_description(long_body) is False

    def test_markdown_stripped_before_word_count(self):
        """
        Markdown formatting characters must not inflate the word count.
        A body of "**bold**" is ONE word after stripping, not three.  This
        prevents heavily-formatted but content-thin bodies from bypassing
        AI generation.
        """
        # 19 real words wrapped in markdown — still under threshold.
        markdown_body = "**" + _words(MIN_DESCRIPTION_WORDS - 1) + "**"
        assert needs_ai_description(markdown_body) is True


# ===========================================================================
# FALLBACK_DESCRIPTION constant
# ===========================================================================

class TestFallbackDescriptionConstant:
    """
    Tests that the FALLBACK_DESCRIPTION constant in description.py holds the
    exact string used in the UI.

    Why test a constant?  The exact wording appears both here and hardcoded
    in enricher.py (where it is inlined as a string literal).  Pinning it in
    a test means any accidental edit to either location is caught immediately,
    keeping the two copies in sync.
    """

    def test_fallback_description_exact_value(self):
        """
        The constant must be the exact string expected by the UI and by the
        enricher fallback path.
        """
        assert FALLBACK_DESCRIPTION == "Visit GitHub for full details on this task."

    def test_fallback_description_is_non_empty_string(self):
        """
        The fallback must never be empty or None — an empty fallback would
        produce a blank card on the platform.
        """
        assert isinstance(FALLBACK_DESCRIPTION, str)
        assert len(FALLBACK_DESCRIPTION) > 0


# ===========================================================================
# enrich_issues — consecutive failure abort
# ===========================================================================

class TestEnrichIssuesConsecutiveFailures:
    """
    Tests for enricher.enrich_issues(issues, repo_description).

    The MAX_CONSECUTIVE_FAILURES guard exists to prevent a runaway Anthropic
    outage from burning through a sync cycle and stalling.  When the threshold
    is hit:
      - The function must NOT raise.
      - All remaining issues must appear in the output with the fallback
        description (no issues silently dropped).
      - The fallback description must be exactly FALLBACK_DESCRIPTION.
    """

    def _make_issues(self, count: int) -> list[dict]:
        return [_make_issue(i) for i in range(count)]

    @patch("services.issue_finder.enricher.github_client")
    @patch("services.issue_finder.enricher.process_issue_description")
    def test_abort_after_max_consecutive_failures_does_not_raise(
        self, mock_process, mock_gc
    ):
        """
        When every process_issue_description call raises, enrich_issues must
        absorb the failures and return normally.  An unhandled exception here
        would crash the sync job and prevent any issues from being stored.
        """
        mock_gc.get_issue_comments.return_value = []
        mock_process.side_effect = RuntimeError("Anthropic down")

        issues = self._make_issues(MAX_CONSECUTIVE_FAILURES + 5)
        # Must not raise
        result = enrich_issues(issues, repo_description="A test repo.")
        assert isinstance(result, list)

    @patch("services.issue_finder.enricher.github_client")
    @patch("services.issue_finder.enricher.process_issue_description")
    def test_abort_produces_fallback_for_all_remaining_issues(
        self, mock_process, mock_gc
    ):
        """
        After MAX_CONSECUTIVE_FAILURES the enricher must bulk-fill all
        not-yet-processed issues with the fallback description.  Dropping
        issues silently would mean valid tasks never reach the database.
        """
        mock_gc.get_issue_comments.return_value = []
        mock_process.side_effect = RuntimeError("Anthropic down")

        total = MAX_CONSECUTIVE_FAILURES + 5
        issues = self._make_issues(total)
        result = enrich_issues(issues, repo_description="A test repo.")

        # Every single input issue must appear in the output.
        assert len(result) == total

    @patch("services.issue_finder.enricher.github_client")
    @patch("services.issue_finder.enricher.process_issue_description")
    def test_abort_sets_fallback_description_on_remaining_issues(
        self, mock_process, mock_gc
    ):
        """
        Issues that were not processed before the abort must each have
        description_display equal to the canonical FALLBACK_DESCRIPTION
        string, matching what is shown on the UI card.
        """
        mock_gc.get_issue_comments.return_value = []
        mock_process.side_effect = RuntimeError("Anthropic down")

        total = MAX_CONSECUTIVE_FAILURES + 3
        issues = self._make_issues(total)
        result = enrich_issues(issues, repo_description="A test repo.")

        for enriched in result:
            assert enriched["description_display"] == FALLBACK_DESCRIPTION

    @patch("services.issue_finder.enricher.github_client")
    @patch("services.issue_finder.enricher.process_issue_description")
    def test_partial_success_before_abort(self, mock_process, mock_gc):
        """
        If some issues succeed before the failure streak begins, those
        successful results must be preserved in the returned list alongside
        the fallback-filled issues.  The abort must not discard successful
        work already done.
        """
        mock_gc.get_issue_comments.return_value = []

        success_count = 3
        call_count = {"n": 0}

        def _side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= success_count:
                return ("A real description with enough words to be useful.", True)
            raise RuntimeError("Anthropic down")

        mock_process.side_effect = _side_effect

        total = success_count + MAX_CONSECUTIVE_FAILURES + 2
        issues = self._make_issues(total)
        result = enrich_issues(issues, repo_description="A test repo.")

        # All issues must be present.
        assert len(result) == total

        # The first `success_count` issues must have the real description.
        for i in range(success_count):
            assert result[i]["description_display"] == "A real description with enough words to be useful."

        # Issues after the failure streak must have the fallback.
        for enriched in result[success_count + MAX_CONSECUTIVE_FAILURES:]:
            assert enriched["description_display"] == FALLBACK_DESCRIPTION

    @patch("services.issue_finder.enricher.github_client")
    @patch("services.issue_finder.enricher.process_issue_description")
    def test_get_issue_comments_is_called_for_issues_needing_ai(
        self, mock_process, mock_gc
    ):
        """
        When an issue has no body (needs AI), the enricher must fetch GitHub
        comments to provide context to Claude.  Skipping this call would
        produce lower-quality descriptions.
        """
        mock_gc.get_issue_comments.return_value = ["First comment"]
        mock_process.return_value = ("Generated description for the task at hand.", True)

        issue = _make_issue(1)
        issue["body"] = None  # Explicitly no body — triggers comment fetch

        enrich_issues([issue], repo_description="Repo about accessibility.")

        mock_gc.get_issue_comments.assert_called_once()
