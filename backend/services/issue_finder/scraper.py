# services/issue_finder/scraper.py
# Fetches raw open issues from GitHub for a set of non-code labels.
# This module is responsible only for talking to GitHub and returning
# structured data — filtering and enrichment happen in separate modules.
#
# Label → contribution_type mapping is defined here because it's tightly
# coupled to what we ask GitHub for. The filter module uses the mapped type,
# not the raw label string.

import datetime as _dt
import logging
from datetime import datetime, timezone
from typing import Optional

from services.github_client import github_client, RateLimitLowError
from services.issue_finder.bounty_detector import detect_bounty

logger = logging.getLogger(__name__)

# Recognised open source SPDX license identifiers.
# Only repos with a license whose spdx_id is in this set will be ingested.
# NOASSERTION and null licenses are always rejected — no exceptions.
# This set is the single source of truth for both the GitHub and GitLab scrapers.
OPEN_SOURCE_LICENSES = frozenset({
    "MIT", "Apache-2.0", "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0",
    "AGPL-3.0", "MPL-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
    "CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "Unlicense", "EUPL-1.2",
    "CDDL-1.0", "EPL-1.0", "EPL-2.0", "WTFPL", "Artistic-2.0",
})

# ── Pagination constants ────────────────────────────────────────────────────
# Maximum number of GitHub API results per page (GitHub cap is 100).
# Used by both scrape_issues_for_label and get_issues_by_label.
_ISSUES_PER_PAGE = 100

# How many pages to fetch per label per repo.  2 pages × 100 = up to 200
# issues per label, giving large repos a fair chance to surface all their
# non-code issues in a single scrape cycle.
ISSUES_PER_LABEL_PAGES_MAX = 2

# ── Discovery query helpers ─────────────────────────────────────────────────
# Used to build date-bounded search queries without hardcoding a year.
# "pushed after two years ago" keeps mid-tier repos in scope even if they
# aren't updated every week.
_PUSHED_AFTER: str = f"{_dt.date.today().year - 2}-01-01"

# GitHub issue Search API queries used for repo discovery.
# Each query targets a different slice of the open source ecosystem so the
# scraper casts a wide net across labels, languages, and star ranges.
#
# Qualifiers that apply to the *repository* when used in issue search:
#   stars:X..Y    — repository star count
#   language:X    — repository primary language
#   pushed:>DATE  — last push date (keeps stale repos out)
#   archived:false — skip repos that no longer accept contributions
#   is:public     — public repos only (implicit for unauthenticated, but explicit is safer)
REPO_DISCOVERY_QUERIES: list[str] = [
    # ── Documentation ─────────────────────────────────────────────────────────
    # Mid-tier (50–500 stars) — active communities that are often overlooked
    f"label:documentation is:open is:issue archived:false stars:50..500 pushed:>{_PUSHED_AFTER}",
    # Larger repos — higher signal-to-noise, worth checking for non-code asks
    f"label:documentation is:open is:issue archived:false stars:500..5000 pushed:>{_PUSHED_AFTER}",
    # Docs with help-wanted — maintainer explicitly wants contributors
    f'label:documentation label:"help wanted" is:open is:issue archived:false stars:50..2000',
    # ── Design ────────────────────────────────────────────────────────────────
    f"label:design is:open is:issue archived:false stars:50..1000 pushed:>{_PUSHED_AFTER}",
    f"label:ux is:open is:issue archived:false stars:50..2000",
    f"label:accessibility is:open is:issue archived:false stars:50..2000 pushed:>{_PUSHED_AFTER}",
    # ── Translation / i18n ────────────────────────────────────────────────────
    f"label:translation is:open is:issue archived:false stars:50..3000",
    f"label:i18n is:open is:issue archived:false stars:50..3000",
    f"label:localization is:open is:issue archived:false stars:50..3000",
    # ── Community / Outreach ──────────────────────────────────────────────────
    f"label:community is:open is:issue archived:false stars:50..2000 pushed:>{_PUSHED_AFTER}",
    f"label:outreach is:open is:issue archived:false stars:50..1000",
    # ── Language-specific documentation ───────────────────────────────────────
    # Targeting language communities separately surfaces repos that use their
    # ecosystem's dominant language and may have different labelling conventions.
    f"label:documentation language:python is:open is:issue archived:false stars:100..1000 pushed:>{_PUSHED_AFTER}",
    f"label:documentation language:javascript is:open is:issue archived:false stars:100..1000 pushed:>{_PUSHED_AFTER}",
    f"label:documentation language:typescript is:open is:issue archived:false stars:100..1000 pushed:>{_PUSHED_AFTER}",
    f"label:documentation language:rust is:open is:issue archived:false stars:100..2000 pushed:>{_PUSHED_AFTER}",
    f"label:documentation language:go is:open is:issue archived:false stars:100..2000 pushed:>{_PUSHED_AFTER}",
    f"label:documentation language:java is:open is:issue archived:false stars:100..1000 pushed:>{_PUSHED_AFTER}",
    # ── Design by language ────────────────────────────────────────────────────
    f"label:design language:python is:open is:issue archived:false stars:50..1000 pushed:>{_PUSHED_AFTER}",
    f"label:design language:javascript is:open is:issue archived:false stars:50..1000 pushed:>{_PUSHED_AFTER}",
    # ── Catch-alls paired with explicit non-code labels ────────────────────────
    f'label:"good first issue" label:documentation is:open is:issue archived:false stars:50..1000',
    f'label:"good first issue" label:design is:open is:issue archived:false stars:50..1000',
    f'label:"help wanted" label:documentation is:open is:issue archived:false stars:50..500',
    f'label:"help wanted" label:design is:open is:issue archived:false stars:50..500',
]

# All labels we actively search for on GitHub.
# Organised by contribution type — the filter module narrows results further.
# Catch-all labels (help-wanted, good-first-issue, etc.) are included but
# filters.py applies extra scrutiny: they must have a non-code signal in the
# title/body to pass through.
NON_CODE_LABELS = [
    # ── Design ──────────────────────────────────────────────────────────────
    "design",
    "needs-design",
    "ux",
    "ui",
    "ui/ux",
    "design-needed",
    "figma",
    "visual",
    "accessibility",
    "a11y",
    # ── Documentation ───────────────────────────────────────────────────────
    "documentation",
    "docs",
    "needs-docs",
    "improve-docs",
    "good-docs",
    "doc-fix",
    "writing",
    "content",
    "technical-writing",
    # ── Translation ─────────────────────────────────────────────────────────
    "translation",
    "i18n",
    "l10n",
    "localization",
    "internationalisation",
    "needs-translation",
    "language",
    # ── Research ────────────────────────────────────────────────────────────
    "research",
    "user-research",
    "needs-research",
    "investigation",
    "discovery",
    # ── Community ───────────────────────────────────────────────────────────
    "community",
    "community-management",
    "outreach",
    "social",
    "devrel",
    "developer-relations",
    "advocacy",
    # ── Marketing ───────────────────────────────────────────────────────────
    "marketing",
    "growth",
    "content-marketing",
    "seo",
    "copywriting",
    # ── Social Media ────────────────────────────────────────────────────────
    "social-media",
    "twitter",
    "announcement",
    # ── Project Management ──────────────────────────────────────────────────
    "project-management",
    "planning",
    "roadmap",
    "triage",
    "needs-triage",
    "organisation",
    # ── PR Review ───────────────────────────────────────────────────────────
    "needs-review",
    "pr-review",
    "review-needed",
    "review-requested",
    # ── Data & Analytics ────────────────────────────────────────────────────
    "analytics",
    "data",
    "metrics",
    "tracking",
    "data-analysis",
    # ── General catch-alls (extra scrutiny applied in filters.py) ───────────
    "help-wanted",
    "good-first-issue",
    "first-timers-only",
    "hacktoberfest",
    "up-for-grabs",
    "contributions-welcome",
    "beginner-friendly",
    "low-hanging-fruit",
]

# Mapping from GitHub label name → contribution_type enum value.
# Labels are lowercased before lookup — GitHub labels are case-insensitive
# but repos use inconsistent casing (e.g. "Design" vs "design").
# Only valid contribution_type_enum values may appear as dict values.
LABEL_TO_CONTRIBUTION_TYPE: dict[str, str] = {
    # Design
    "design": "design",
    "needs-design": "design",
    "ux": "design",
    "ui": "design",
    "ui/ux": "design",
    "design-needed": "design",
    "figma": "design",
    "visual": "design",
    "accessibility": "design",
    "a11y": "design",
    # Documentation
    "documentation": "documentation",
    "docs": "documentation",
    "needs-docs": "documentation",
    "improve-docs": "documentation",
    "good-docs": "documentation",
    "doc-fix": "documentation",
    "writing": "documentation",
    "content": "documentation",
    "technical-writing": "documentation",
    # Translation
    "translation": "translation",
    "i18n": "translation",
    "l10n": "translation",
    "localization": "translation",
    "internationalisation": "translation",
    "needs-translation": "translation",
    "language": "translation",
    # Research
    "research": "research",
    "user-research": "research",
    "needs-research": "research",
    "investigation": "research",
    "discovery": "research",
    # Community
    "community": "community",
    "community-management": "community",
    "outreach": "community",
    "social": "community",
    "devrel": "community",
    "developer-relations": "community",
    "advocacy": "community",
    # Marketing
    "marketing": "marketing",
    "growth": "marketing",
    "content-marketing": "marketing",
    "seo": "marketing",
    "copywriting": "marketing",
    # Social Media
    "social-media": "social_media",
    "twitter": "social_media",
    "announcement": "social_media",
    # Project Management
    "project-management": "project_management",
    "planning": "project_management",
    "roadmap": "project_management",
    "triage": "project_management",
    "needs-triage": "project_management",
    "organisation": "project_management",
    # PR Review
    "needs-review": "pr_review",
    "pr-review": "pr_review",
    "review-needed": "pr_review",
    "review-requested": "pr_review",
    # Data & Analytics
    "analytics": "data_analytics",
    "data": "data_analytics",
    "metrics": "data_analytics",
    "tracking": "data_analytics",
    "data-analysis": "data_analytics",
    # Catch-alls — contribution type resolved from other labels at query time
    "help-wanted": "other",
    "good-first-issue": "other",
    "first-timers-only": "other",
    "hacktoberfest": "other",
    "up-for-grabs": "other",
    "contributions-welcome": "other",
    "beginner-friendly": "other",
    "low-hanging-fruit": "other",
}


def map_labels_to_contribution_type(labels: list[str]) -> str:
    """
    Map a list of GitHub label names to a single contribution_type enum value.

    Tries each label in order and returns the first match. Falls back to
    "other" if none of the labels match our mapping. Labels are lowercased
    before comparison so casing differences in repos don't cause missed matches.

    Args:
        labels: List of GitHub label name strings

    Returns:
        A contribution_type enum string (e.g. "design", "documentation")
    """
    for label in labels:
        mapped = LABEL_TO_CONTRIBUTION_TYPE.get(label.lower())
        if mapped:
            return mapped
    return "other"


def build_project_data(owner: str, repo_name: str) -> Optional[dict]:
    """
    Fetch and structure project metadata from GitHub for a single repository.

    Called once per repo during a scrape run. Returns a dict ready to be
    passed to the database layer. Returns None if the repo cannot be fetched
    so callers can skip it cleanly.

    Args:
        owner:     GitHub repository owner (e.g. "chaoss")
        repo_name: GitHub repository name (e.g. "augur")

    Returns:
        Dict of structured project fields, or None on failure.
    """
    repo_data = github_client.get_repo(owner, repo_name)
    if not repo_data:
        logger.warning(
            "Could not fetch repo metadata — skipping",
            extra={"owner": owner, "repo": repo_name},
        )
        return None

    # Reject private repos — Nocos is strictly an open source platform
    if repo_data.get("private", False):
        logger.info(
            "Skipping repo — private repository",
            extra={"owner": owner, "repo": repo_name},
        )
        return None

    # Reject archived repos — no contributions are possible on archived repos
    if repo_data.get("archived", False):
        logger.info(
            "Skipping repo — archived repository",
            extra={"owner": owner, "repo": repo_name},
        )
        return None

    # Reject repos without a recognised open source license
    license_obj = repo_data.get("license") or {}
    spdx_id: Optional[str] = license_obj.get("spdx_id") if license_obj else None
    if not spdx_id or spdx_id == "NOASSERTION" or spdx_id not in OPEN_SOURCE_LICENSES:
        logger.info(
            "Skipping repo — no open source license",
            extra={"owner": owner, "repo": repo_name, "license": spdx_id},
        )
        return None

    last_commit_raw = github_client.get_last_commit_date(owner, repo_name)
    last_commit_date: Optional[datetime] = None
    if last_commit_raw:
        try:
            last_commit_date = datetime.fromisoformat(
                last_commit_raw.replace("Z", "+00:00")
            )
        except ValueError:
            logger.warning(
                "Could not parse last commit date",
                extra={"owner": owner, "repo": repo_name, "raw": last_commit_raw},
            )

    # Build the social_links JSON — github is always present, others only if found.
    # The homepage field in the GitHub API maps to the project's website URL.
    social_links = {
        "github": f"https://github.com/{owner}/{repo_name}",
        "twitter": None,
        "discord": None,
        "slack": None,
        "linkedin": None,
        "youtube": None,
    }

    return {
        "name": repo_data.get("full_name", f"{owner}/{repo_name}"),
        "github_url": repo_data.get("html_url", f"https://github.com/{owner}/{repo_name}"),
        "github_owner": owner,
        "github_repo": repo_name,
        "description": repo_data.get("description") or "",
        "website_url": repo_data.get("homepage") or None,
        "avatar_url": repo_data.get("owner", {}).get("avatar_url", ""),
        "social_links": social_links,
        "last_commit_date": last_commit_date,
        "is_archived": repo_data.get("archived", False),
    }


def scrape_issues_for_label(
    owner: str,
    repo_name: str,
    label: str,
    page: int = 1,
    per_page: int = _ISSUES_PER_PAGE,
) -> list[dict]:
    """
    Fetch open issues from a single repo filtered by a single label.

    Returns a list of structured issue dicts. Each dict is self-contained —
    it includes the label list, contribution type, and the raw body so the
    enricher can decide whether to generate an AI description.

    This function does not filter or enrich issues — it only fetches and
    structures the raw data. Separation of concerns keeps each module testable.

    Args:
        owner:     Repository owner
        repo_name: Repository name
        label:     The label to filter by (one of NON_CODE_LABELS)
        page:      Page number for pagination
        per_page:  Results per page (max 100, default _ISSUES_PER_PAGE)

    Returns:
        List of structured issue dicts, or [] if the fetch fails.
    """
    raw_issues = github_client.get_issues_by_label(
        owner=owner,
        repo=repo_name,
        label=label,
        page=page,
        per_page=per_page,
    )

    structured = []
    for issue in raw_issues:
        # Pull requests appear in the issues endpoint — skip them.
        # PRs have a "pull_request" key; real issues do not.
        if "pull_request" in issue:
            continue

        label_names = [lbl["name"] for lbl in issue.get("labels", [])]
        contribution_type = map_labels_to_contribution_type(label_names)

        # Parse GitHub's ISO 8601 datetime string into a Python datetime
        created_at_raw = issue.get("created_at")
        created_at: Optional[datetime] = None
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(
                    created_at_raw.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        issue_dict: dict = {
            "github_issue_id": issue["id"],
            "github_issue_number": issue["number"],
            "title": issue.get("title", ""),
            "body": issue.get("body"),  # Raw body — may be None or empty
            "labels": label_names,
            "contribution_type": contribution_type,
            "github_issue_url": issue.get("html_url", ""),
            "github_created_at": created_at,
            "state": issue.get("state", "open"),
            "comments_url": issue.get("comments_url", ""),
            "github_owner": owner,
            "github_repo": repo_name,
        }

        # Detect real-money bounty — adds is_bounty + bounty_amount fields
        is_bounty, bounty_amount = detect_bounty(issue_dict)
        issue_dict["is_bounty"] = is_bounty
        issue_dict["bounty_amount"] = bounty_amount

        structured.append(issue_dict)

    return structured


def scrape_repo(owner: str, repo_name: str) -> tuple[Optional[dict], list[dict]]:
    """
    Scrape all non-code issues from a single GitHub repository.

    Iterates over all NON_CODE_LABELS and collects issues for each.
    Deduplicates by github_issue_id — an issue with two matching labels
    (e.g. "design" and "good-first-issue") should only appear once.

    Args:
        owner:     Repository owner
        repo_name: Repository name

    Returns:
        Tuple of (project_data, issues_list).
        project_data is None if the repo could not be fetched.
        issues_list may be empty if no matching issues were found.
    """
    project_data = build_project_data(owner, repo_name)
    if not project_data:
        return None, []

    seen_ids: set[int] = set()
    all_issues: list[dict] = []

    for label in NON_CODE_LABELS:
        try:
            # Paginate: fetch up to ISSUES_PER_LABEL_PAGES_MAX pages per label.
            # A page shorter than _ISSUES_PER_PAGE means we've hit the last page.
            for page_num in range(1, ISSUES_PER_LABEL_PAGES_MAX + 1):
                page_issues = scrape_issues_for_label(
                    owner, repo_name, label, page=page_num
                )
                for issue in page_issues:
                    issue_id = issue["github_issue_id"]
                    # Deduplicate — same issue can match multiple labels
                    if issue_id not in seen_ids:
                        seen_ids.add(issue_id)
                        all_issues.append(issue)

                # Fewer results than a full page means this was the last page
                if len(page_issues) < _ISSUES_PER_PAGE:
                    break

        except RateLimitLowError:
            # Rate limit hit mid-scrape — stop here and process what we have.
            # The next sync cycle will pick up where we left off.
            logger.warning(
                "Rate limit hit mid-scrape — stopping early",
                extra={"owner": owner, "repo": repo_name, "label": label},
            )
            break
        except Exception as e:
            # A single label failure should not abort the whole repo scrape
            logger.error(
                "Error scraping label — skipping",
                extra={"owner": owner, "repo": repo_name, "label": label, "error": str(e)},
            )
            continue

    logger.info(
        "Repo scrape complete",
        extra={"owner": owner, "repo": repo_name, "issues_found": len(all_issues)},
    )
    return project_data, all_issues


def discover_repos_via_search(max_repos_per_query: int = 15) -> list[tuple[str, str]]:
    """
    Discover new repos to scrape by running REPO_DISCOVERY_QUERIES via the
    GitHub Search API.

    Each query targets a different slice of the ecosystem (label, language,
    star range). Results are deduplicated so a repo that appears in multiple
    queries is only returned once.

    Callers (run_discovery in sync.py) are responsible for filtering out repos
    already in the database before scraping them.

    Args:
        max_repos_per_query: Maximum unique repos to extract per search query.
                             Capped to keep the total scrape time and GitHub
                             API quota usage predictable.

    Returns:
        Deduplicated list of (owner, repo_name) tuples found across all queries.
    """
    seen: set[tuple[str, str]] = set()
    repos: list[tuple[str, str]] = []

    for query in REPO_DISCOVERY_QUERIES:
        try:
            issues = github_client.search_issues(query, per_page=100, page=1)
        except RateLimitLowError:
            logger.warning(
                "Rate limit hit during repo discovery — stopping early",
                extra={"query": query[:80]},
            )
            break
        except Exception as e:
            logger.error(
                "Discovery query failed — skipping",
                extra={"query": query[:80], "error": str(e)},
            )
            continue

        query_new = 0
        for item in issues:
            # Each search result includes a repository_url like:
            # "https://api.github.com/repos/owner/repo"
            repo_url = item.get("repository_url", "")
            if not repo_url:
                continue
            parts = repo_url.rstrip("/").split("/")
            if len(parts) < 2:
                continue
            owner_name, repo_name = parts[-2], parts[-1]
            pair = (owner_name, repo_name)
            if pair not in seen:
                seen.add(pair)
                repos.append(pair)
                query_new += 1
                if query_new >= max_repos_per_query:
                    break

        logger.debug(
            "Discovery query complete",
            extra={"query": query[:80], "new_repos": query_new},
        )

    logger.info(
        "Repo discovery complete",
        extra={"total_repos": len(repos), "queries_run": len(REPO_DISCOVERY_QUERIES)},
    )
    return repos
