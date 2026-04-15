# services/sync.py
# 6-hour freshness sync job for the Nocos platform.
# Keeps the database accurate by checking active tasks and projects
# against their current state on GitHub.
#
# Run by APScheduler every 6 hours in the background — it never blocks
# API request handling (SKILLS.md Section 15).
#
# What the sync does (features.md Section 7):
#   a. Issue closed on GitHub    → is_active=False, hidden_reason="closed"
#   b. Issue > 14 days old       → is_active=False, hidden_reason="stale"
#   c. Repo archived on GitHub   → all tasks + project set to inactive
#   d. Issue body changed        → regenerate AI description
#   e. Last commit date changed  → recalculate activity_score/status

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from models.project import Project
from models.task import Task
from services.github_client import github_client, RateLimitLowError
from services.issue_finder.enricher import should_regenerate_description, enrich_issue
from services.issue_finder.filters import MAX_ISSUE_AGE_DAYS
from services.cache import app_cache

logger = logging.getLogger(__name__)

# How often the sync runs
SYNC_INTERVAL_HOURS = 6


# ─── Activity Score & Status ───────────────────────────────────────────────────

def calculate_activity_status(last_commit_date: Optional[datetime]) -> tuple[str, int]:
    """
    Calculate a project's activity_status and activity_score from last commit date.

    Status thresholds (features.md Section 2):
      - active:   last commit within 30 days → score 80–100
      - slow:     last commit 30–90 days ago → score 40–79
      - inactive: last commit over 90 days   → score 0–39

    Args:
        last_commit_date: The datetime of the most recent commit (UTC)

    Returns:
        Tuple of (activity_status, activity_score)
    """
    if last_commit_date is None:
        return ("inactive", 0)

    now = datetime.now(tz=timezone.utc)
    if last_commit_date.tzinfo is None:
        last_commit_date = last_commit_date.replace(tzinfo=timezone.utc)

    days_since = (now - last_commit_date).days

    if days_since <= 30:
        # Active: score scales from 100 (today) down to 80 (30 days ago)
        score = max(80, 100 - days_since)
        return ("active", score)
    elif days_since <= 90:
        # Slow: score scales from 79 (31 days) down to 40 (90 days)
        score = max(40, 79 - (days_since - 30))
        return ("slow", score)
    else:
        # Inactive: score scales from 39 down to 0
        score = max(0, 39 - (days_since - 90))
        return ("inactive", score)


# ─── Issue Sync Checks ─────────────────────────────────────────────────────────

def _hide_task(task: Task, reason: str, session: Session) -> None:
    """
    Mark a single task as hidden with the given reason.

    Uses soft delete — the row stays in the database for audit purposes
    but is_active=False means it won't appear anywhere on the platform.

    Args:
        task:    The Task ORM object to hide
        reason:  The hidden_reason enum value ("closed", "stale", "archived")
        session: Active SQLAlchemy session
    """
    task.is_active = False
    task.hidden_reason = reason
    task.hidden_at = datetime.now(tz=timezone.utc)
    session.add(task)
    logger.info(
        "Task hidden",
        extra={"task_id": str(task.id), "reason": reason},
    )


def _sync_single_task(task: Task, session: Session) -> None:
    """
    Check a single active task against its current GitHub state.

    Applies all five freshness checks in sequence. If the task needs
    to be hidden it's marked immediately. If only the description has
    changed, the AI generator is re-run.

    Args:
        task:    Active Task ORM object to check
        session: Active SQLAlchemy session
    """
    owner = task.project.github_owner
    repo = task.project.github_repo

    # Check (b): age — no GitHub call needed, just compare dates
    if task.github_created_at:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=MAX_ISSUE_AGE_DAYS)
        created = task.github_created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            _hide_task(task, "stale", session)
            return  # No further checks needed once hidden

    # Remaining checks require a GitHub API call — skip if we don't have a number
    if not task.github_issue_number:
        return

    try:
        # Fetch the exact issue by number — avoids the false-closed bug where
        # page-1 of all issues misses the specific issue in large repos.
        current = github_client.get_single_issue(owner, repo, task.github_issue_number)

    except RateLimitLowError:
        # Rate limit hit — skip this task and try again next cycle
        logger.warning(
            "Rate limit low — skipping task sync",
            extra={"task_id": str(task.id)},
        )
        return
    except Exception as e:
        logger.error(
            "Error fetching issue during sync",
            extra={"task_id": str(task.id), "error": str(e)},
        )
        return

    if current is None:
        # Issue not found in open issues — assume it was closed
        _hide_task(task, "closed", session)
        return

    # Check (a): closed status
    if current.get("state", "open") == "closed":
        _hide_task(task, "closed", session)
        return

    # Check (d): issue body has changed — regenerate description
    current_body = current.get("body")
    if should_regenerate_description(task.description_original, current_body):
        logger.info(
            "Issue body changed — regenerating AI description",
            extra={"task_id": str(task.id)},
        )
        issue_dict = {
            "body": current_body,
            "github_owner": owner,
            "github_repo": repo,
            "github_issue_number": task.github_issue_number,
            "title": task.title,
            "labels": task.labels or [],
        }
        enriched = enrich_issue(
            issue_dict,
            repo_description=task.project.description or "",
        )
        task.description_original = current_body
        task.description_display = enriched["description_display"]
        task.is_ai_generated = enriched["is_ai_generated"]
        session.add(task)
        # Invalidate the cached detail response so the next request gets fresh data
        app_cache.invalidate_issue(str(task.id))


def _sync_project(project: Project, session: Session) -> None:
    """
    Check a single active project's GitHub state and update activity scores.

    Handles check (c) — archived repo — and check (e) — activity recalculation.

    Args:
        project: Active Project ORM object
        session: Active SQLAlchemy session
    """
    try:
        repo_data = github_client.get_repo(project.github_owner, project.github_repo)
    except RateLimitLowError:
        logger.warning(
            "Rate limit low — skipping project sync",
            extra={"project_id": str(project.id)},
        )
        return
    except Exception as e:
        logger.error(
            "Error fetching repo during project sync",
            extra={"project_id": str(project.id), "error": str(e)},
        )
        return

    # Check (c): repo is archived on GitHub
    if repo_data.get("archived", False):
        logger.info(
            "Repo archived — deactivating project and all tasks",
            extra={"project_id": str(project.id)},
        )
        project.is_active = False
        session.add(project)
        # Hide all tasks belonging to this project
        for task in session.query(Task).filter(
            Task.project_id == project.id,
            Task.is_active == True,
        ).all():
            _hide_task(task, "archived", session)
        return

    # Check (e): recalculate activity score from last commit date
    last_commit_raw = github_client.get_last_commit_date(
        project.github_owner, project.github_repo
    )
    if last_commit_raw:
        try:
            last_commit_date = datetime.fromisoformat(
                last_commit_raw.replace("Z", "+00:00")
            )
            status, score = calculate_activity_status(last_commit_date)
            project.activity_status = status
            project.activity_score = score
            project.last_commit_date = last_commit_date
            session.add(project)
            # Invalidate cached project so the next request sees updated activity
            app_cache.invalidate_project(project.github_owner, project.github_repo)
        except ValueError:
            logger.warning(
                "Could not parse last commit date during sync",
                extra={"project_id": str(project.id), "raw": last_commit_raw},
            )


# ─── Main Sync Entry Point ─────────────────────────────────────────────────────

def run_sync(session_factory) -> None:
    """
    Run a full freshness sync pass over all active tasks and projects.

    Called by APScheduler every 6 hours. Opens a DB session, iterates over
    all active projects then all active tasks, applies freshness checks, and
    commits changes in a single transaction.

    Args:
        session_factory: SQLAlchemy sessionmaker — injected to keep this
                         function testable without a real database connection.
    """
    logger.info("Freshness sync started")
    start_time = datetime.now(tz=timezone.utc)

    with session_factory() as session:
        try:
            # Sync projects first — archived projects deactivate their tasks,
            # which prevents redundant task-level checks below
            active_projects = session.query(Project).filter(
                Project.is_active == True
            ).all()

            for project in active_projects:
                _sync_project(project, session)

            # Sync individual tasks (only those still active after project sync)
            active_tasks = (
                session.query(Task)
                .filter(Task.is_active == True)
                .all()
            )

            for task in active_tasks:
                _sync_single_task(task, session)

            session.commit()

            duration = (datetime.now(tz=timezone.utc) - start_time).total_seconds()
            logger.info(
                "Freshness sync complete",
                extra={
                    "projects_checked": len(active_projects),
                    "tasks_checked": len(active_tasks),
                    "duration_seconds": round(duration, 2),
                },
            )

        except Exception as e:
            session.rollback()
            logger.exception("Freshness sync failed — rolled back", extra={"error": str(e)})


# ─── Scrape & Ingest New Issues ───────────────────────────────────────────────

def _ingest_repo_issues(
    project_data: dict,
    raw_issues: list[dict],
    session: Session,
) -> tuple[bool, int]:
    """
    Upsert a project record and insert any newly discovered tasks.

    Filters the raw scraped issues through the staleness/code-only/closed
    checks, enriches survivors with AI descriptions where needed, then
    inserts only issues that don't already exist in the database
    (matched by github_issue_id).

    Args:
        project_data: Structured project dict from scraper.build_project_data()
        raw_issues:   Raw issue dicts from scraper.scrape_repo()
        session:      Active SQLAlchemy session (caller commits)

    Returns:
        Tuple of (project_was_new, new_tasks_inserted_count)
    """
    from services.issue_finder.filters import apply_filters
    from services.issue_finder.enricher import enrich_issues

    owner = project_data["github_owner"]
    repo = project_data["github_repo"]

    # Upsert the project — create it if it doesn't exist yet
    project = session.query(Project).filter(
        Project.github_owner == owner,
        Project.github_repo == repo,
    ).first()

    project_is_new = False
    if project is None:
        last_commit_date = project_data.get("last_commit_date")
        status, score = calculate_activity_status(last_commit_date)
        project = Project(
            name=project_data["name"],
            github_url=project_data["github_url"],
            github_owner=owner,
            github_repo=repo,
            description=project_data.get("description") or "",
            website_url=project_data.get("website_url"),
            avatar_url=project_data["avatar_url"],
            social_links=project_data.get("social_links", {}),
            activity_score=score,
            activity_status=status,
            last_commit_date=last_commit_date,
            is_active=not project_data.get("is_archived", False),
        )
        session.add(project)
        session.flush()  # Populate project.id before inserting tasks
        project_is_new = True
        logger.info(
            "New project created",
            extra={"owner": owner, "repo": repo},
        )

    # Apply staleness / code-only / closed filters
    filtered = apply_filters(raw_issues)
    if not filtered:
        return project_is_new, 0

    # Enrich with AI descriptions where the body is too short
    enriched = enrich_issues(
        filtered,
        repo_description=project_data.get("description") or "",
    )

    # Insert new tasks; re-activate any that were incorrectly hidden
    new_count = 0
    for issue in enriched:
        github_issue_id = issue.get("github_issue_id")

        if github_issue_id is not None:
            existing = (
                session.query(Task)
                .filter(Task.github_issue_id == github_issue_id)
                .first()
            )
            if existing:
                # The scraper only returns open issues — if we see a hidden task
                # here it was wrongly marked inactive (e.g. by the old broken sync
                # that couldn't find the issue in page-1 of a large repo).
                # Re-activate it so it becomes visible again.
                if not existing.is_active:
                    existing.is_active = True
                    existing.hidden_reason = None
                    existing.hidden_at = None
                    session.add(existing)
                    new_count += 1
                continue

        task = Task(
            project_id=project.id,
            github_issue_id=github_issue_id,
            github_issue_number=issue.get("github_issue_number"),
            title=issue.get("title", ""),
            description_original=issue.get("body"),
            description_display=issue.get(
                "description_display",
                "Visit GitHub for full details on this task.",
            ),
            is_ai_generated=issue.get("is_ai_generated", False),
            labels=issue.get("labels", []),
            contribution_type=issue.get("contribution_type", "other"),
            is_paid=False,
            difficulty=None,
            source="github_scrape",
            github_created_at=issue.get("github_created_at"),
            github_issue_url=issue.get("github_issue_url", ""),
            is_active=True,
        )
        session.add(task)
        new_count += 1

    logger.info(
        "Repo ingest complete",
        extra={
            "owner": owner,
            "repo": repo,
            "raw": len(raw_issues),
            "filtered": len(filtered),
            "new_tasks": new_count,
        },
    )
    return project_is_new, new_count


def run_scrape(extra_repos: list[str], session_factory) -> dict:
    """
    Scrape GitHub for non-code issues and ingest new tasks into the database.

    Scrapes two sets of repos:
      1. All active projects already in the database (so the scheduled sync
         picks up new issues on existing tracked projects).
      2. Any additional "owner/repo" strings passed by the caller — used by
         the manual trigger endpoint to seed the database with new projects.

    Deduplicates by github_issue_id so re-running is safe.

    Args:
        extra_repos:     List of "owner/repo" strings (may be empty)
        session_factory: SQLAlchemy sessionmaker

    Returns:
        Dict: { projects_scraped, new_tasks_added, duration_seconds }
    """
    from services.issue_finder.scraper import scrape_repo

    logger.info("Scrape run started", extra={"extra_repos": extra_repos})
    start_time = datetime.now(tz=timezone.utc)

    # Parse "owner/repo" strings — silently skip malformed entries
    extra_pairs: list[tuple[str, str]] = []
    for repo_str in extra_repos:
        parts = repo_str.strip().split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            extra_pairs.append((parts[0], parts[1]))
        else:
            logger.warning(
                "Skipping malformed repo string",
                extra={"repo": repo_str},
            )

    total_projects_scraped = 0
    total_new_tasks = 0

    with session_factory() as session:
        try:
            # Existing DB projects
            db_projects = (
                session.query(Project)
                .filter(Project.is_active == True)
                .all()
            )
            db_pairs = {(p.github_owner, p.github_repo) for p in db_projects}

            # Merge: DB projects first, then extra repos not already in DB
            all_pairs = list(db_pairs) + [
                pair for pair in extra_pairs if pair not in db_pairs
            ]

            for owner, repo_name in all_pairs:
                logger.info(
                    "Scraping repo",
                    extra={"owner": owner, "repo": repo_name},
                )
                try:
                    project_data, raw_issues = scrape_repo(owner, repo_name)
                    if project_data is None:
                        logger.warning(
                            "Could not fetch project metadata — skipping",
                            extra={"owner": owner, "repo": repo_name},
                        )
                        continue

                    _, new_tasks = _ingest_repo_issues(
                        project_data, raw_issues, session
                    )
                    total_projects_scraped += 1
                    total_new_tasks += new_tasks

                except RateLimitLowError:
                    logger.warning(
                        "GitHub rate limit hit — stopping scrape early",
                        extra={"owner": owner, "repo": repo_name},
                    )
                    break
                except Exception as e:
                    logger.error(
                        "Repo scrape failed — skipping",
                        extra={
                            "owner": owner,
                            "repo": repo_name,
                            "error": str(e),
                        },
                    )
                    continue

            session.commit()

        except Exception as e:
            session.rollback()
            logger.exception(
                "Scrape run failed — rolled back",
                extra={"error": str(e)},
            )
            raise

    duration = (datetime.now(tz=timezone.utc) - start_time).total_seconds()
    stats = {
        "projects_scraped": total_projects_scraped,
        "new_tasks_added": total_new_tasks,
        "duration_seconds": round(duration, 2),
    }
    logger.info("Scrape run complete", extra=stats)
    return stats


# ─── Scheduler Setup ──────────────────────────────────────────────────────────

def create_scheduler(session_factory) -> BackgroundScheduler:
    """
    Create and return a configured APScheduler BackgroundScheduler.

    The scheduler is not started here — call scheduler.start() from the
    FastAPI lifespan handler so it starts after the app is ready and stops
    cleanly on shutdown.

    Args:
        session_factory: SQLAlchemy sessionmaker passed through to run_sync()

    Returns:
        Configured BackgroundScheduler (not yet started)
    """
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=run_sync,
        trigger="interval",
        hours=SYNC_INTERVAL_HOURS,
        kwargs={"session_factory": session_factory},
        id="freshness_sync",
        name="Nocos 6-hour freshness sync",
        # Replace existing job if the scheduler is restarted mid-interval
        replace_existing=True,
    )

    logger.info(
        "Sync scheduler configured",
        extra={"interval_hours": SYNC_INTERVAL_HOURS},
    )
    return scheduler
