# services/featured_projects_service.py
# Live-fetch functions for the Featured Projects section.
#
# Two categories are returned:
#   most_active     — public repos pushed to in the last 7 days, >100 stars,
#                     ranked by a weighted score of weekly commits + new issues + stars.
#   new_promising   — public repos created in the last 90 days, >50 stars,
#                     sorted by star count (newest rising stars).
#
# Results are cached in Redis for 7 days (TTL_FEATURED).
# The weekly APScheduler job in sync.py calls these functions and writes
# results to the featured_projects DB table so /api/v1/featured can serve
# from the DB on subsequent requests without hitting GitHub.
#
# Open-source license enforcement:
#   Only repos whose license.spdx_id is in OPEN_SOURCE_LICENSES are included.
#   This is the same allowlist used by the scraper (scraper.py §10).

import logging
from datetime import date, timedelta
from typing import Optional

from services.github_client import github_client, RateLimitLowError
from services.retry import retry_call
from services.cache import app_cache, TTL_FEATURED
from services.issue_finder.scraper import OPEN_SOURCE_LICENSES

logger = logging.getLogger(__name__)

# Number of featured projects to return per category
FEATURED_LIMIT = 6

# Weights for the most_active composite score
_W_COMMITS = 0.5
_W_ISSUES = 0.3
_W_STARS = 0.2

# Search query constants
_DAYS_SINCE_PUSH = 7       # repos must have been pushed to within this many days
_MIN_STARS_ACTIVE = 100    # minimum star count for most_active
_MAX_AGE_DAYS_NEW = 90     # repos must be created within this many days
_MIN_STARS_NEW = 50        # minimum star count for new_promising


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _iso_date(days_ago: int) -> str:
    """Return an ISO-8601 date string for N days before today (UTC)."""
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _is_open_source(repo: dict) -> bool:
    """
    Return True if the repo carries a recognised open-source license.

    The GitHub search API returns repos without a license too — we must
    filter them out so Nocos only surfaces genuinely open projects.
    """
    license_info = repo.get("license") or {}
    spdx = license_info.get("spdx_id") or ""
    return spdx in OPEN_SOURCE_LICENSES


def _get_weekly_commits(owner: str, repo: str) -> int:
    """
    Return total commits across all branches for the past week.

    Uses the /repos/{owner}/{repo}/stats/commit_activity endpoint which
    returns a 52-week array; we take the last entry (most recent week).
    Returns 0 on any error or if GitHub hasn't computed stats yet (202).
    """
    cache_key = f"weekly_commits:{owner}:{repo}"
    cached = app_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        github_client._check_rate_limit()
    except RateLimitLowError:
        return 0

    def _fetch() -> int:
        response = github_client._http.get(
            f"/repos/{owner}/{repo}/stats/commit_activity"
        )
        if response.status_code == 202:
            # GitHub is computing stats asynchronously — try again next cycle
            return 0
        response.raise_for_status()
        weeks = response.json()
        if not weeks:
            return 0
        return weeks[-1].get("total", 0)

    count = retry_call(
        _fetch,
        fallback=0,
        context={"owner": owner, "repo": repo},
        log=logger,
    )

    # Cache for 1 hour — this endpoint is expensive (counts as a rate-limited call)
    app_cache.set(cache_key, count, 3600)
    return count


def _search_repos(query: str, sort: str = "stars", per_page: int = 30) -> list[dict]:
    """
    Call the GitHub repository search API and return the items list.

    Args:
        query:    GitHub search query string (e.g. "stars:>100 is:public")
        sort:     GitHub sort field ("stars", "forks", "updated")
        per_page: Number of results to request (max 100)

    Returns:
        List of GitHub repository objects, or [] on error / rate limit.
    """
    try:
        github_client._check_rate_limit()
    except RateLimitLowError:
        logger.warning("Rate limit low — skipping featured project search")
        return []

    def _fetch() -> list[dict]:
        response = github_client._http.get(
            "/search/repositories",
            params={
                "q": query,
                "sort": sort,
                "order": "desc",
                "per_page": per_page,
            },
        )
        response.raise_for_status()
        return response.json().get("items", [])

    return retry_call(
        _fetch,
        fallback=[],
        context={"query": query},
        log=logger,
    )


def _build_project_dict(repo: dict, category: str, weekly_commits: int = 0) -> dict:
    """
    Serialize a GitHub repo search result into the FeaturedProject shape.

    Args:
        repo:           Raw GitHub repository object
        category:       "most_active" or "new_promising"
        weekly_commits: Commit count for the past 7 days (most_active only)

    Returns:
        Dict matching the FeaturedProjectResponse schema
    """
    license_info = repo.get("license") or {}
    owner_info = repo.get("owner") or {}
    return {
        "repo_full_name": repo.get("full_name", ""),
        "name": repo.get("name", ""),
        "description": repo.get("description") or "",
        "language": repo.get("language"),
        "stars": repo.get("stargazers_count", 0),
        "stars_gained_this_week": None,
        "forks": repo.get("forks_count", 0),
        "open_issues_count": repo.get("open_issues_count", 0),
        "homepage": repo.get("homepage") or None,
        "license": license_info.get("spdx_id"),
        "topics": repo.get("topics") or [],
        "weekly_commits": weekly_commits,
        "avatar_url": owner_info.get("avatar_url", ""),
        "github_url": repo.get("html_url", ""),
        "category": category,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def fetch_most_active_projects() -> list[dict]:
    """
    Find the most actively-developed open-source repos over the past 7 days.

    Methodology:
      1. Search GitHub for public repos pushed to in the last 7 days, >100 stars.
      2. Fetch weekly commit counts for each candidate (up to 30 fetched, top 15 used).
      3. Rank by composite score: commits×0.5 + open_issues×0.3 + stars×0.2
         (normalised to 0-100 so the three signals are comparable).
      4. Filter to open-source licenses only.
      5. Return the top FEATURED_LIMIT (6) results.

    Results are cached for 7 days (TTL_FEATURED) so the scheduler job only
    hits the GitHub API once per week.

    Returns:
        List of up to 6 project dicts.
    """
    cache_key = "featured:most_active"
    cached = app_cache.get(cache_key)
    if cached is not None:
        logger.info("most_active: returning cached results")
        return cached

    since = _iso_date(_DAYS_SINCE_PUSH)
    query = (
        f"pushed:>{since} stars:>{_MIN_STARS_ACTIVE} "
        f"is:public archived:false"
    )

    logger.info("Fetching most_active candidates from GitHub Search")
    repos = _search_repos(query, sort="updated", per_page=30)

    # Filter to open-source only before making commit-activity calls
    repos = [r for r in repos if _is_open_source(r)]

    if not repos:
        logger.warning("most_active: no open-source repos found in search results")
        return []

    # Fetch weekly commit counts — only for the first 15 (rate limit budget)
    candidates: list[dict] = []
    for repo in repos[:15]:
        owner_login = (repo.get("owner") or {}).get("login", "")
        repo_name = repo.get("name", "")
        if not owner_login or not repo_name:
            continue
        commits = _get_weekly_commits(owner_login, repo_name)
        candidates.append((repo, commits))

    if not candidates:
        return []

    # Normalise each signal to 0–100 before applying weights
    max_commits = max(c for _, c in candidates) or 1
    max_issues = max(r.get("open_issues_count", 0) for r, _ in candidates) or 1
    max_stars = max(r.get("stargazers_count", 0) for r, _ in candidates) or 1

    def _score(repo: dict, commits: int) -> float:
        norm_commits = (commits / max_commits) * 100
        norm_issues = (repo.get("open_issues_count", 0) / max_issues) * 100
        norm_stars = (repo.get("stargazers_count", 0) / max_stars) * 100
        return (
            norm_commits * _W_COMMITS
            + norm_issues * _W_ISSUES
            + norm_stars * _W_STARS
        )

    ranked = sorted(candidates, key=lambda x: _score(x[0], x[1]), reverse=True)
    top = ranked[:FEATURED_LIMIT]

    results = [
        _build_project_dict(repo, "most_active", weekly_commits=commits)
        for repo, commits in top
    ]

    app_cache.set(cache_key, results, TTL_FEATURED)
    logger.info("most_active: cached %d results", len(results))
    return results


def fetch_new_promising_projects() -> list[dict]:
    """
    Find recently-created open-source repos with strong early star traction.

    Methodology:
      1. Search GitHub for public repos created in the last 90 days, >50 stars.
      2. Sort by star count descending (GitHub Search handles this natively).
      3. Filter to open-source licenses only.
      4. Return the top FEATURED_LIMIT (6) results.

    Results are cached for 7 days (TTL_FEATURED).

    Returns:
        List of up to 6 project dicts.
    """
    cache_key = "featured:new_promising"
    cached = app_cache.get(cache_key)
    if cached is not None:
        logger.info("new_promising: returning cached results")
        return cached

    since = _iso_date(_MAX_AGE_DAYS_NEW)
    query = (
        f"created:>{since} stars:>{_MIN_STARS_NEW} "
        f"is:public archived:false"
    )

    logger.info("Fetching new_promising candidates from GitHub Search")
    repos = _search_repos(query, sort="stars", per_page=30)

    # Filter to open-source only
    repos = [r for r in repos if _is_open_source(r)]

    if not repos:
        logger.warning("new_promising: no open-source repos found in search results")
        return []

    top = repos[:FEATURED_LIMIT]
    results = [_build_project_dict(repo, "new_promising") for repo in top]

    app_cache.set(cache_key, results, TTL_FEATURED)
    logger.info("new_promising: cached %d results", len(results))
    return results
