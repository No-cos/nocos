# services/gitlab_sync.py
# GitLab issue scraper for the Nocos platform.
# Fetches open non-code issues from GitLab.com, enriches them with AI
# descriptions where needed, and upserts them into the Nocos database.
#
# Mirrors the GitHub scraper pattern (github_client.py + scraper.py) so
# both pipelines share the same filter, enrichment, and storage logic.
#
# Rate limit notes:
#   - Unauthenticated: ~60 requests/min
#   - Authenticated (PRIVATE-TOKEN): 2,000 requests/min
#   - If GITLAB_TOKEN is missing, scraping proceeds unauthenticated (warn only)
#   - HTTP 429 raises GitLabRateLimitError — callers stop paging and continue
#
# Pagination: GitLab returns up to 100 issues per page. We loop until an
# empty page is returned, pausing PAGE_DELAY_SECONDS between pages to stay
# well within rate limits.
#
# Deduplication: we do NOT use github_issue_id for GitLab issues because
# GitLab and GitHub issue IDs are independent sequences that can collide in
# the unique constraint. Instead we deduplicate by (project_id, issue iid),
# which is guaranteed unique per project on GitLab.

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import redis

from config import config
from models.project import Project
from models.task import Task
from services.issue_finder.enricher import enrich_issues
from services.issue_finder.filters import apply_filters
from services.issue_finder.scraper import OPEN_SOURCE_LICENSES
from services.retry import retry_call

# Pre-compute uppercase set for case-insensitive matching against GitLab's
# lowercase license keys (e.g. "mit", "apache-2.0" → "MIT", "APACHE-2.0").
_OPEN_SOURCE_LICENSES_UPPER = frozenset(lic.upper() for lic in OPEN_SOURCE_LICENSES)

logger = logging.getLogger(__name__)

# GitLab REST API v4 base URL
GITLAB_API_BASE = "https://gitlab.com/api/v4"

# GitLab supports up to 100 per page — always request the maximum
GITLAB_PER_PAGE = 100

# Pause between page fetches — keeps us well within GitLab rate limits
PAGE_DELAY_SECONDS = 0.5

# Redis cache TTLs (seconds) — mirror the GitHub client strategy (SKILLS.md §9)
CACHE_TTL_ISSUES = 1800   # 30 minutes — issue lists change frequently
CACHE_TTL_PROJECT = 3600  # 1 hour    — project metadata is stable


# ─── Label → contribution_type mapping ────────────────────────────────────────

# Labels we actively search for on GitLab.com.
# Mirrors NON_CODE_LABELS in the GitHub scraper so both pipelines produce
# the same contribution type distribution.
NON_CODE_LABELS: list[str] = [
    "design",
    "ux",
    "ui",
    "a11y",
    "accessibility",
    "documentation",
    "docs",
    "translation",
    "research",
    "community",
    "content",
    "marketing",
    "good-first-issue",
    "community management",
]

# GitLab label name → contribution_type_enum value.
# Keys are compared lowercase so casing in individual repos does not matter.
LABEL_TO_CONTRIBUTION_TYPE: dict[str, str] = {
    "design": "design",
    "ux": "design",
    "ui": "design",
    "a11y": "design",
    "accessibility": "design",
    "documentation": "documentation",
    "docs": "documentation",
    "translation": "translation",
    "research": "research",
    "community": "community",
    "community management": "community",
    "content": "documentation",
    "marketing": "marketing",
    "pr-review": "pr_review",
    "pr review": "pr_review",
    "data": "data_analytics",
    "analytics": "data_analytics",
    "good-first-issue": "other",
    "good first issue": "other",
}


# ─── Exceptions ────────────────────────────────────────────────────────────────

class GitLabRateLimitError(Exception):
    """
    Raised when GitLab returns HTTP 429 (Too Many Requests).

    Callers should stop paging for the current label and continue with the
    next. This is expected behaviour during large scrape runs and is not a bug.
    """
    pass


class GitLabAPIError(Exception):
    """Raised when the GitLab API returns a non-2xx, non-429 error response."""
    pass


# ─── Activity status (local copy avoids circular import with sync.py) ─────────

def _calculate_activity_status(last_commit_date: Optional[datetime]) -> tuple[str, int]:
    """
    Calculate activity_status and activity_score from a project's last activity.

    Mirrors calculate_activity_status() in sync.py. Kept here to avoid a
    circular import (sync.py imports this module; we cannot import sync.py).

    Thresholds (features.md Section 2):
      - active:   last activity within 30 days → score 80–100
      - slow:     last activity 30–90 days ago → score 40–79
      - inactive: last activity over 90 days   → score 0–39

    Args:
        last_commit_date: Most recent activity datetime (UTC), or None.

    Returns:
        Tuple of (activity_status, activity_score).
    """
    if last_commit_date is None:
        return ("inactive", 0)

    now = datetime.now(tz=timezone.utc)
    if last_commit_date.tzinfo is None:
        last_commit_date = last_commit_date.replace(tzinfo=timezone.utc)

    days_since = (now - last_commit_date).days

    if days_since <= 30:
        score = max(80, 100 - days_since)
        return ("active", score)
    elif days_since <= 90:
        score = max(40, 79 - (days_since - 30))
        return ("slow", score)
    else:
        score = max(0, 39 - (days_since - 90))
        return ("inactive", score)


# ─── GitLab API Client ─────────────────────────────────────────────────────────

class GitLabClient:
    """
    Authenticated GitLab API client with Redis caching and retry logic.

    Reads GITLAB_TOKEN from the environment at construction time using
    os.getenv() directly — not via config.py — because this token is optional
    and must not prevent app startup if absent.

    If the token is missing, requests are made unauthenticated. GitLab allows
    this but enforces a much lower rate limit (~60 req/min). A startup warning
    is logged so operators know to add the token for better coverage.

    Usage:
        issues = gitlab_client.get_issues("design", page=1)
        project = gitlab_client.get_project(12345)
    """

    def __init__(self) -> None:
        # os.getenv directly — GITLAB_TOKEN is optional and NOT in config.validate()
        token: str = os.getenv("GITLAB_TOKEN", "")

        headers: dict[str, str] = {"Accept": "application/json"}
        if token:
            # GitLab personal access tokens use the PRIVATE-TOKEN header
            headers["PRIVATE-TOKEN"] = token
        else:
            logger.warning(
                "GITLAB_TOKEN not set — GitLab scraper will run unauthenticated "
                "(rate limited to ~60 req/min). Add GITLAB_TOKEN for full coverage."
            )

        self._http = httpx.Client(
            base_url=GITLAB_API_BASE,
            headers=headers,
            timeout=15.0,
        )
        self._redis = self._connect_redis()
        self._token_present: bool = bool(token)

    def _connect_redis(self) -> Optional[redis.Redis]:
        """
        Connect to Redis for response caching. Returns None if unavailable.

        Redis is optional — the client degrades gracefully without it (every
        fetch hits the API directly). Expected in local dev without Redis.
        """
        try:
            r = redis.from_url(config.REDIS_URL, decode_responses=True)
            r.ping()
            return r
        except Exception:
            logger.warning("Redis unavailable — GitLab responses will not be cached")
            return None

    # ─── Cache helpers ─────────────────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[object]:
        """Return a cached value from Redis, or None if missing or unavailable."""
        if not self._redis:
            return None
        try:
            value = self._redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    def _cache_set(self, key: str, value: object, ttl_seconds: int) -> None:
        """Store a value in Redis with the given TTL. Fails silently."""
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl_seconds, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(
                "Redis cache write failed",
                extra={"key": key, "error": str(e)},
            )

    # ─── API methods ───────────────────────────────────────────────────────────

    def get_issues(self, label: str, page: int = 1) -> list:
        """
        Fetch one page of open GitLab issues matching a single label.

        Uses scope=all so we see issues across all public projects, not just
        those the token owner is a member of. Returns at most GITLAB_PER_PAGE
        results. Returns [] when the page is empty (end of results).

        Cached for 30 minutes per (label, page) pair.
        Raises GitLabRateLimitError on HTTP 429 so callers can stop paging.

        Args:
            label: GitLab label name to filter by (e.g. "design")
            page:  1-based page number

        Returns:
            List of GitLab issue objects as dicts, or [] on failure.
        """
        cache_key = f"gitlab:issues:{label}:{page}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        def _fetch() -> list:
            response = self._http.get(
                "/issues",
                params={
                    "scope": "all",
                    "state": "opened",
                    "labels": label,
                    "page": page,
                    "per_page": GITLAB_PER_PAGE,
                },
            )
            if response.status_code == 429:
                raise GitLabRateLimitError(
                    f"GitLab rate limit reached (label='{label}', page={page})"
                )
            response.raise_for_status()
            return response.json()

        issues = retry_call(
            _fetch,
            fallback=[],
            context={"label": label, "page": page},
            log=logger,
        )

        if issues:
            self._cache_set(cache_key, issues, CACHE_TTL_ISSUES)
            logger.info(
                "Fetched GitLab issues page",
                extra={"label": label, "page": page, "count": len(issues)},
            )
        return issues  # type: ignore[return-value]

    def get_project(self, project_id: int) -> Optional[dict]:
        """
        Fetch GitLab project metadata by numeric project ID.

        Returns name, namespace, avatar, description, website, and archived
        status. Cached for 1 hour — project metadata changes infrequently.

        Args:
            project_id: GitLab project's numeric ID (from issue.project_id)

        Returns:
            GitLab project object as a dict, or None if not found or on error.
        """
        cache_key = f"gitlab:project:{project_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        def _fetch() -> Optional[dict]:
            response = self._http.get(f"/projects/{project_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

        data = retry_call(
            _fetch,
            fallback=None,
            context={"project_id": project_id},
            log=logger,
        )
        if data:
            self._cache_set(cache_key, data, CACHE_TTL_PROJECT)
        return data  # type: ignore[return-value]

    def close(self) -> None:
        """Close the underlying HTTP client. Call on application shutdown."""
        self._http.close()


# Module-level singleton — import gitlab_client from this module everywhere.
# Constructed at import time so the missing-token warning appears at startup.
gitlab_client = GitLabClient()


# ─── Label mapping ─────────────────────────────────────────────────────────────

def map_labels_to_contribution_type(labels: list[str]) -> str:
    """
    Map a list of GitLab label names to a single contribution_type enum value.

    Tries each label in order and returns the first match. Falls back to
    "other" if no label matches the mapping. Labels are lowercased before
    comparison so casing differences across repos don't cause missed matches.

    Args:
        labels: List of GitLab label name strings

    Returns:
        A contribution_type_enum string (e.g. "design", "documentation").
    """
    for label in labels:
        mapped = LABEL_TO_CONTRIBUTION_TYPE.get(label.lower())
        if mapped:
            return mapped
    return "other"


# ─── Project data builder ──────────────────────────────────────────────────────

def _build_project_data(raw_project: dict) -> dict:
    """
    Transform a raw GitLab project API response into the project_data dict
    format expected by _ingest_gitlab_repo().

    Mirrors build_project_data() in the GitHub scraper (scraper.py) so both
    pipelines produce identically shaped project dicts.

    The project web_url is stored in github_url (the column name is a legacy
    artefact — it is used as the canonical project URL regardless of source).
    GitLab's last_activity_at is the best available proxy for last commit date
    without a separate commits API call.

    Args:
        raw_project: GitLab project object from GET /projects/{id}

    Returns:
        Structured project_data dict ready for _ingest_gitlab_repo().
    """
    namespace = raw_project.get("namespace", {})
    namespace_path: str = namespace.get("path", "")
    repo_path: str = raw_project.get("path", "")
    web_url: str = raw_project.get(
        "web_url",
        f"https://gitlab.com/{namespace_path}/{repo_path}",
    )

    # GitLab projects often have no avatar — fall back to namespace avatar
    avatar_url: str = (
        raw_project.get("avatar_url")
        or namespace.get("avatar_url")
        or ""
    )

    # last_activity_at is a reasonable proxy for last commit date on GitLab
    last_commit_date: Optional[datetime] = None
    last_activity_raw: Optional[str] = raw_project.get("last_activity_at")
    if last_activity_raw:
        try:
            last_commit_date = datetime.fromisoformat(
                last_activity_raw.replace("Z", "+00:00")
            )
        except ValueError:
            logger.warning(
                "Could not parse GitLab last_activity_at",
                extra={"project_id": raw_project.get("id"), "raw": last_activity_raw},
            )

    # GitLab projects don't expose Twitter/Discord/Slack in the API response.
    # We record the GitLab URL and leave the rest null.
    social_links: dict = {
        "github": None,
        "gitlab": web_url,
        "twitter": None,
        "discord": None,
        "slack": None,
        "linkedin": None,
        "youtube": None,
    }

    return {
        "name": raw_project.get("name_with_namespace", f"{namespace_path}/{repo_path}"),
        "github_url": web_url,          # Column name is legacy — stores canonical project URL
        "github_owner": namespace_path,
        "github_repo": repo_path,
        "description": raw_project.get("description") or "",
        "website_url": raw_project.get("web_url") or None,
        "avatar_url": avatar_url,
        "social_links": social_links,
        "last_commit_date": last_commit_date,
        "is_archived": raw_project.get("archived", False),
    }


# ─── Per-label paginated scraper ───────────────────────────────────────────────

def _scrape_label(label: str) -> list[dict]:
    """
    Fetch all pages of GitLab issues matching a single label and structure them.

    Paginates until an empty response page is returned or a rate limit is hit.
    Pauses PAGE_DELAY_SECONDS between pages to stay within rate limits.
    Fetches project metadata once per unique project_id (Redis-cached for 1h).

    Args:
        label: GitLab label string (e.g. "design", "documentation")

    Returns:
        List of structured issue dicts with an embedded "_project_data" key.
        Raw, unfiltered — filtering and enrichment happen in run_gitlab_scrape().
    """
    issues: list[dict] = []
    # project_id → raw project dict (populated lazily, cached in Redis)
    seen_projects: dict[int, Optional[dict]] = {}
    page = 1

    while True:
        try:
            raw_page = gitlab_client.get_issues(label, page)
        except GitLabRateLimitError:
            logger.warning(
                "GitLab rate limit reached — stopping label scrape early",
                extra={"label": label, "page": page},
            )
            break
        except Exception as e:
            logger.error(
                "Error fetching GitLab issues — stopping label scrape",
                extra={"label": label, "page": page, "error": str(e)},
            )
            break

        if not raw_page:
            # Empty page means we've reached the last page of results
            break

        for raw_issue in raw_page:
            project_id: int = raw_issue.get("project_id", 0)
            if not project_id:
                continue

            # Fetch project metadata once per project — subsequent calls hit cache
            if project_id not in seen_projects:
                seen_projects[project_id] = gitlab_client.get_project(project_id)

            raw_project = seen_projects[project_id]
            if not raw_project:
                logger.warning(
                    "Could not fetch GitLab project metadata — skipping issue",
                    extra={"project_id": project_id, "issue_id": raw_issue.get("id")},
                )
                continue

            # Skip archived projects — no contributions possible
            if raw_project.get("archived", False):
                seen_projects[project_id] = None  # Cache skip so other labels skip fast
                continue

            # Skip projects without a recognised open source license.
            # GitLab returns a "license" object with a lowercase "key" field
            # (e.g. "mit", "apache-2.0"). We normalise to uppercase before
            # checking against OPEN_SOURCE_LICENSES.
            license_obj = raw_project.get("license") or {}
            license_key = (license_obj.get("key") or "").upper() if license_obj else ""
            if not license_key or license_key not in _OPEN_SOURCE_LICENSES_UPPER:
                logger.info(
                    "Skipping GitLab project — no open source license",
                    extra={
                        "project_id": project_id,
                        "license": license_obj.get("key") if license_obj else None,
                    },
                )
                seen_projects[project_id] = None  # Cache skip so other labels skip fast
                continue

            label_names: list[str] = raw_issue.get("labels", [])
            contribution_type = map_labels_to_contribution_type(label_names)

            # Parse GitLab's ISO 8601 datetime string (may have trailing Z)
            created_at: Optional[datetime] = None
            created_at_raw: Optional[str] = raw_issue.get("created_at")
            if created_at_raw:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_raw.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            namespace_path = raw_project.get("namespace", {}).get("path", "")
            repo_path = raw_project.get("path", "")

            issues.append({
                # github_issue_id intentionally None — GitLab and GitHub issue IDs
                # are independent sequences and can collide in the UNIQUE constraint.
                # We deduplicate GitLab issues by (project_id, issue iid) instead.
                "github_issue_id": None,
                "github_issue_number": raw_issue.get("iid"),  # project-scoped number
                "title": raw_issue.get("title", ""),
                "body": raw_issue.get("description"),         # raw GitLab body
                "labels": label_names,
                "contribution_type": contribution_type,
                "github_issue_url": raw_issue.get("web_url", ""),
                "github_created_at": created_at,
                "state": "open",  # we only request opened=True issues
                "github_owner": namespace_path,
                "github_repo": repo_path,
                # Embedded project metadata — used by _ingest_gitlab_repo().
                # Stripped before passing to the enricher (not part of issue schema).
                "_project_data": _build_project_data(raw_project),
            })

        page += 1
        time.sleep(PAGE_DELAY_SECONDS)

    logger.info(
        "GitLab label scrape complete",
        extra={"label": label, "issues_found": len(issues)},
    )
    return issues


# ─── Database ingest ───────────────────────────────────────────────────────────

def _ingest_gitlab_repo(
    project_data: dict,
    issues: list[dict],
    session,
) -> int:
    """
    Upsert a GitLab project and its enriched issues into the database.

    Mirrors _ingest_repo_issues() in sync.py but uses (project_id, iid) as
    the deduplication key rather than github_issue_id — safe for GitLab
    because iid is unique per project on GitLab.com.

    Projects are matched by github_url (the canonical project URL). If the
    project does not yet exist in the database, it is created here.

    Args:
        project_data: Structured project dict from _build_project_data()
        issues:       Filtered and enriched issue dicts for this project
        session:      Active SQLAlchemy session (caller commits)

    Returns:
        Number of new tasks inserted (or re-activated).
    """
    owner = project_data["github_owner"]
    repo = project_data["github_repo"]

    # Match project by canonical URL — unique across both GitHub and GitLab projects
    project = (
        session.query(Project)
        .filter(Project.github_url == project_data["github_url"])
        .first()
    )

    if project is None:
        last_commit_date = project_data.get("last_commit_date")
        status, score = _calculate_activity_status(last_commit_date)
        project = Project(
            name=project_data["name"],
            github_url=project_data["github_url"],
            github_owner=owner,
            github_repo=repo,
            description=project_data.get("description") or "",
            website_url=project_data.get("website_url"),
            avatar_url=project_data.get("avatar_url") or "",
            social_links=project_data.get("social_links", {}),
            activity_score=score,
            activity_status=status,
            last_commit_date=last_commit_date,
            is_active=not project_data.get("is_archived", False),
        )
        session.add(project)
        session.flush()  # Populate project.id before inserting child tasks
        logger.info(
            "New GitLab project created",
            extra={"owner": owner, "repo": repo},
        )

    new_count = 0
    for issue in issues:
        issue_number = issue.get("github_issue_number")

        # Deduplicate by (project_id, github_issue_number) — safe for GitLab.
        # iid is unique per project, and we own the project row above.
        if issue_number is not None:
            existing = (
                session.query(Task)
                .filter(
                    Task.project_id == project.id,
                    Task.github_issue_number == issue_number,
                )
                .first()
            )
            if existing:
                # Re-activate if it was incorrectly hidden during a previous sync
                if not existing.is_active:
                    existing.is_active = True
                    existing.hidden_reason = None
                    existing.hidden_at = None
                    session.add(existing)
                    new_count += 1
                continue

        task = Task(
            project_id=project.id,
            github_issue_id=None,           # Not used for GitLab — avoids ID collisions
            github_issue_number=issue_number,
            title=issue.get("title", ""),
            description_original=issue.get("body"),
            description_display=issue.get(
                "description_display",
                "Visit GitLab for full details on this task.",
            ),
            is_ai_generated=issue.get("is_ai_generated", False),
            labels=issue.get("labels", []),
            contribution_type=issue.get("contribution_type", "other"),
            is_paid=False,
            difficulty=None,
            source="github_scrape",         # Reuses existing enum value — no migration needed
            github_created_at=issue.get("github_created_at"),
            github_issue_url=issue.get("github_issue_url", ""),
            is_active=True,
        )
        session.add(task)
        new_count += 1

    logger.info(
        "GitLab project ingest complete",
        extra={"owner": owner, "repo": repo, "new_tasks": new_count},
    )
    return new_count


# ─── Main entry point ──────────────────────────────────────────────────────────

def run_gitlab_scrape(session_factory) -> dict:
    """
    Run a full GitLab scrape: fetch issues, filter, enrich with AI, upsert.

    Called by the APScheduler job every 2 hours and also available manually
    via POST /api/v1/sync/trigger.

    Flow:
      1. For each non-code label: fetch all pages from GET /api/v4/issues
      2. Deduplicate across labels — one issue can match multiple labels
      3. Apply the same staleness / code-only / closed filters as GitHub
      4. Group surviving issues by their parent project URL
      5. For each project group: enrich with AI descriptions, upsert into DB

    Args:
        session_factory: SQLAlchemy sessionmaker (injected for testability)

    Returns:
        Dict with keys: projects_scraped, new_tasks_added, duration_seconds
    """
    if not gitlab_client._token_present:
        logger.warning(
            "run_gitlab_scrape: GITLAB_TOKEN not set — proceeding unauthenticated"
        )

    logger.info("GitLab scrape run started")
    start_time = datetime.now(tz=timezone.utc)

    # Step 1 + 2: scrape all labels, deduplicate by (project_url, iid)
    # Using a set of (canonical_url, iid) tuples avoids the integer-ID
    # collision risk and correctly handles issues labelled with multiple
    # matching tags (they only appear once in the final list).
    seen: set[tuple[str, int]] = set()
    raw_issues: list[dict] = []

    for label in NON_CODE_LABELS:
        try:
            label_issues = _scrape_label(label)
        except Exception as e:
            # A single label failure must not abort the whole scrape run
            logger.error(
                "GitLab label scrape failed — skipping label",
                extra={"label": label, "error": str(e)},
            )
            continue

        for issue in label_issues:
            project_url = issue.get("_project_data", {}).get("github_url", "")
            iid = issue.get("github_issue_number") or 0
            key = (project_url, iid)
            if key not in seen:
                seen.add(key)
                raw_issues.append(issue)

    logger.info(
        "GitLab raw issues collected",
        extra={"total": len(raw_issues), "labels_searched": len(NON_CODE_LABELS)},
    )

    # Step 3: apply the same filters as the GitHub pipeline
    # (staleness, code-only labels, closed state)
    filtered = apply_filters(raw_issues)

    # Step 4: group surviving issues by their parent project URL
    by_project: dict[str, list[dict]] = {}
    for issue in filtered:
        project_url = issue.get("_project_data", {}).get("github_url", "")
        if not project_url:
            continue
        by_project.setdefault(project_url, []).append(issue)

    total_projects = 0
    total_new_tasks = 0

    # Step 5: enrich with AI descriptions, then upsert each project's issues
    with session_factory() as session:
        try:
            for project_url, project_issues in by_project.items():
                project_data = project_issues[0]["_project_data"]
                repo_description = project_data.get("description") or ""

                # Strip the pipeline-internal _project_data key before passing
                # to enrich_issues — it is not part of the standard issue schema
                clean_issues = [
                    {k: v for k, v in iss.items() if k != "_project_data"}
                    for iss in project_issues
                ]

                try:
                    enriched = enrich_issues(
                        clean_issues,
                        repo_description=repo_description,
                    )
                    new_count = _ingest_gitlab_repo(project_data, enriched, session)
                    total_projects += 1
                    total_new_tasks += new_count

                except Exception as e:
                    # One project failure must not abort the rest
                    logger.error(
                        "GitLab project ingest failed — skipping project",
                        extra={"project_url": project_url, "error": str(e)},
                    )
                    continue

            session.commit()

        except Exception as e:
            session.rollback()
            logger.exception(
                "GitLab scrape run failed — transaction rolled back",
                extra={"error": str(e)},
            )
            raise

    duration = (datetime.now(tz=timezone.utc) - start_time).total_seconds()
    stats: dict = {
        "projects_scraped": total_projects,
        "new_tasks_added": total_new_tasks,
        "duration_seconds": round(duration, 2),
    }
    logger.info("GitLab scrape run complete", extra=stats)
    return stats
