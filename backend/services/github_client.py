# services/github_client.py
# GitHub API wrapper for the Nocos backend.
# All GitHub API access goes through this module — never use requests or httpx
# directly in other modules. This centralises rate limit handling and caching.
#
# Rate limit strategy (per SKILLS.md Section 9):
#   1. Before every request, check remaining quota from Redis cache (TTL 1 min)
#   2. If fewer than 50 requests remain, raise RateLimitLowError
#   3. Callers catch RateLimitLowError and fall back to cached data
#   4. This prevents the sync job from exhausting the quota and blocking
#      user-facing requests

import json
import logging
from typing import Any, Optional

import httpx
import redis

from config import config
from services.retry import retry_call

logger = logging.getLogger(__name__)

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Redis key patterns — documented here so they're easy to find and update
REDIS_KEY_RATE_LIMIT = "github:rate_limit"
REDIS_KEY_PROJECT = "project:{owner}:{repo}"
REDIS_KEY_ISSUES = "issues:{label}:{page}"
REDIS_KEY_ISSUE = "issue:{github_id}"

# Thresholds
RATE_LIMIT_MINIMUM = 50   # Fall back to cache if remaining drops below this
RATE_LIMIT_WARN_PCT = 20  # Log a warning if remaining falls below 20%


class RateLimitLowError(Exception):
    """
    Raised when GitHub API rate limit remaining drops below RATE_LIMIT_MINIMUM.

    Callers should catch this and return cached data instead.
    This is expected behaviour during heavy sync periods — not a bug.
    """
    pass


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns a non-2xx response."""
    pass


class GitHubClient:
    """
    Authenticated GitHub API client with rate limit handling and Redis caching.

    Uses httpx for async-compatible HTTP requests. All responses are cached
    in Redis to minimise API calls and protect against rate limit exhaustion.

    Usage:
        client = GitHubClient()
        repo = await client.get_repo("chaoss", "augur")
        issues = await client.get_issues("chaoss", "augur", label="design")
    """

    def __init__(self) -> None:
        self._http = httpx.Client(
            base_url=GITHUB_API_BASE,
            headers={
                # Authenticated requests get 5,000 req/hour vs 60 unauthenticated
                "Authorization": f"Bearer {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )
        self._redis = self._connect_redis()

    def _connect_redis(self) -> Optional[redis.Redis]:
        """
        Connect to Redis. Returns None if Redis is unavailable.

        Redis is used for caching only — the client degrades gracefully
        without it. We never raise here; a missing Redis just means no cache.
        """
        try:
            r = redis.from_url(config.REDIS_URL, decode_responses=True)
            r.ping()
            return r
        except Exception:
            # Redis unavailable — log a warning and continue without cache.
            # This is acceptable in local development without Redis running.
            logger.warning("Redis unavailable — GitHub responses will not be cached")
            return None

    # ─── Rate Limit ────────────────────────────────────────────────────────────

    def get_rate_limit_remaining(self) -> int:
        """
        Return the number of GitHub API requests remaining in the current window.

        Checks Redis cache first (TTL 1 min) to avoid a network call on every
        request. Falls back to a live API call if the cache is empty.
        """
        # Try the cache first to avoid a round trip on every check
        if self._redis:
            cached = self._redis.get(REDIS_KEY_RATE_LIMIT)
            if cached:
                return int(cached)

        try:
            response = self._http.get("/rate_limit")
            response.raise_for_status()
            data = response.json()
            remaining = data["rate"]["remaining"]

            # Cache for 1 minute — frequent enough to stay accurate
            if self._redis:
                self._redis.setex(REDIS_KEY_RATE_LIMIT, 60, remaining)

            return remaining
        except Exception as e:
            logger.warning("Could not fetch rate limit status", extra={"error": str(e)})
            # Return a safe default — callers will proceed conservatively
            return 100

    def _check_rate_limit(self) -> None:
        """
        Raise RateLimitLowError if fewer than RATE_LIMIT_MINIMUM requests remain.

        Call this before every GitHub API request. If the limit is low, the
        caller falls back to Redis cache rather than making a live API call.
        """
        remaining = self.get_rate_limit_remaining()

        # Warn at 20% of the 5,000 request hourly limit
        warn_threshold = 5000 * (RATE_LIMIT_WARN_PCT / 100)
        if remaining < warn_threshold:
            logger.warning(
                "GitHub rate limit is low",
                extra={"remaining": remaining, "threshold": warn_threshold},
            )

        if remaining < RATE_LIMIT_MINIMUM:
            raise RateLimitLowError(
                f"Only {remaining} GitHub API requests remaining. Using cache fallback."
            )

    # ─── Cache Helpers ─────────────────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[Any]:
        """Return a cached value from Redis, or None if not found."""
        if not self._redis:
            return None
        try:
            value = self._redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    def _cache_set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store a value in Redis with the given TTL."""
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            # Cache write failure is not fatal — log and continue
            logger.warning("Redis cache write failed", extra={"key": key, "error": str(e)})

    # ─── Repository Info ───────────────────────────────────────────────────────

    def get_repo(self, owner: str, repo: str) -> dict:
        """
        Fetch repository metadata from GitHub.

        Returns project name, description, avatar, website, and archived status.
        Cached for 1 hour — repo metadata rarely changes.

        Uses retry_call() for up to 3 attempts with exponential backoff (1s, 2s, 4s).
        Rate limit errors short-circuit immediately — they do not consume retry budget.

        Args:
            owner: GitHub repository owner (e.g. "chaoss")
            repo:  GitHub repository name (e.g. "augur")

        Returns:
            GitHub repository object as a dict, or {} on failure.
        """
        cache_key = REDIS_KEY_PROJECT.format(owner=owner, repo=repo)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            self._check_rate_limit()
        except RateLimitLowError:
            logger.warning(
                "Rate limit low — returning empty repo",
                extra={"owner": owner, "repo": repo},
            )
            return {}

        def _fetch() -> dict:
            response = self._http.get(f"/repos/{owner}/{repo}")
            response.raise_for_status()
            return response.json()

        data = retry_call(
            _fetch,
            fallback={},
            context={"owner": owner, "repo": repo},
            log=logger,
        )

        if data:
            self._cache_set(cache_key, data, ttl_seconds=3600)  # 1 hour
            logger.info(
                "Fetched repo from GitHub",
                extra={"owner": owner, "repo": repo},
            )
        return data

    def get_last_commit_date(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetch the date of the most recent commit to the default branch.

        Used to calculate activity_status (active / slow / inactive).
        Cached for 30 minutes. Retries up to 3 times with exponential backoff.

        Args:
            owner: Repository owner
            repo:  Repository name

        Returns:
            ISO 8601 datetime string, or None if unavailable.
        """
        cache_key = f"commits:{owner}:{repo}:latest"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            self._check_rate_limit()
        except RateLimitLowError:
            return None

        def _fetch() -> Optional[str]:
            response = self._http.get(
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": 1},
            )
            response.raise_for_status()
            commits = response.json()
            if not commits:
                return None
            return commits[0]["commit"]["committer"]["date"]

        date = retry_call(
            _fetch,
            fallback=None,
            context={"owner": owner, "repo": repo},
            log=logger,
        )
        if date:
            self._cache_set(cache_key, date, ttl_seconds=1800)  # 30 minutes
        return date

    # ─── Issues ────────────────────────────────────────────────────────────────

    def get_issues_by_label(
        self,
        owner: str,
        repo: str,
        label: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list:
        """
        Fetch open issues from a repository filtered by a single label.

        Only returns open issues — closed issues are handled by the sync job
        (it marks existing tasks as hidden when it detects they've been closed).
        Cached for 30 minutes.

        Args:
            owner:    Repository owner
            repo:     Repository name
            label:    Label name to filter by (e.g. "design", "documentation")
            page:     Page number for pagination
            per_page: Number of issues per page (max 100)

        Returns:
            List of GitHub issue objects, or [] on failure.
        """
        cache_key = REDIS_KEY_ISSUES.format(label=label, page=page)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            self._check_rate_limit()
        except RateLimitLowError:
            logger.warning(
                "Rate limit low — returning cached or empty issues",
                extra={"owner": owner, "repo": repo, "label": label},
            )
            return self._cache_get(cache_key) or []

        def _fetch() -> list:
            response = self._http.get(
                f"/repos/{owner}/{repo}/issues",
                params={
                    "labels": label,
                    "state": "open",
                    "page": page,
                    "per_page": per_page,
                },
            )
            response.raise_for_status()
            return response.json()

        issues = retry_call(
            _fetch,
            fallback=[],
            context={"owner": owner, "repo": repo, "label": label},
            log=logger,
        )
        if issues:
            self._cache_set(cache_key, issues, ttl_seconds=1800)  # 30 minutes
            logger.info(
                "Fetched issues from GitHub",
                extra={
                    "owner": owner,
                    "repo": repo,
                    "label": label,
                    "count": len(issues),
                },
            )
        return issues

    def get_issue_comments(
        self, owner: str, repo: str, issue_number: int, limit: int = 3
    ) -> list:
        """
        Fetch the first N comments on a GitHub issue.

        Comments often contain more context than the issue body itself.
        They're passed to Claude to improve description quality.
        Cached for 30 minutes.

        Args:
            owner:        Repository owner
            repo:         Repository name
            issue_number: The issue number (not ID)
            limit:        Maximum number of comments to return

        Returns:
            List of comment body strings (text only, no metadata).
        """
        cache_key = f"comments:{owner}:{repo}:{issue_number}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            self._check_rate_limit()
            response = self._http.get(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                params={"per_page": limit},
            )
            response.raise_for_status()
            comments = [c["body"] for c in response.json()[:limit]]

            self._cache_set(cache_key, comments, ttl_seconds=1800)
            return comments

        except RateLimitLowError:
            return []

        except Exception as e:
            logger.error(
                "Error fetching issue comments",
                extra={"owner": owner, "repo": repo, "issue_number": issue_number},
            )
            return []

    def close(self) -> None:
        """Close the underlying HTTP client. Call on application shutdown."""
        self._http.close()


# Module-level singleton — import github_client from this module everywhere.
# Avoids creating multiple connections and makes mocking in tests straightforward.
github_client = GitHubClient()
