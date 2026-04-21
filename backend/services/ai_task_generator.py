# services/ai_task_generator.py
# AI Task Generator service for Nocos.
#
# Analyses any open source GitHub repository and generates specific non-code
# contribution tasks using Claude — even when the repo has no formal GitHub
# issues for non-code work.
#
# Two separate functions keep the preview/publish flow clean:
#   preview_tasks_for_repo()  — fetch + generate, returns list[dict], saves nothing
#   publish_tasks_for_repo()  — saves the previewed tasks to the database
#
# Security:
#   - ANTHROPIC_API_KEY read from config only — never hardcoded
#   - README content is never logged (can contain PII/sensitive project info)
#   - Only repos passing the OPEN_SOURCE_LICENSES check are processed
#   - All generated tasks are flagged with source="ai_generated" for auditability

import json
import logging
import re
from typing import Optional

from config import config
from services.github_client import github_client
from services.issue_finder.scraper import OPEN_SOURCE_LICENSES

logger = logging.getLogger(__name__)

# The model to use for task generation.
# claude-sonnet-4-5 balances quality and cost; matches the enrichment service.
CLAUDE_MODEL = "claude-sonnet-4-5"

# Maximum number of tasks Claude is asked to produce per call.
TASKS_PER_REPO = 6

# Categories Claude may assign.  Must match contribution_type_enum values in the DB.
VALID_CATEGORIES = {
    "design", "documentation", "translation",
    "community", "marketing", "research",
}

# Difficulty → estimated hours mapping used to validate Claude's output.
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
VALID_HOURS = {3, 6, 10}

# ── Generation prompt ──────────────────────────────────────────────────────────
#
# Design principles:
#   - Asks for exactly TASKS_PER_REPO tasks so parsing is predictable.
#   - Instructs Claude to read the existing issues and avoid duplicates.
#   - Restricts to non-technical categories so no coding tasks slip through.
#   - Requests clean JSON with no prose so extraction is trivial.
#   - README is passed in truncated form — never logged here.

_GENERATION_PROMPT = """\
You are a contribution opportunity analyst for Nocos, a platform that connects \
non-technical contributors with open source projects.

Your job: analyse this GitHub repository and generate {task_count} specific, \
actionable contribution tasks that do NOT require writing code.

━━ REPOSITORY INFORMATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name:        {repo_name}
Description: {description}
Language:    {language}
Stars:       {stars}
Topics:      {topics}
License:     {license}

Top-level files/folders:
{file_structure}

README excerpt (first 3000 characters):
{readme}

━━ EXISTING OPEN ISSUES (avoid duplicating these) ━━━━━━━━━━━━━━
{existing_issues}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate exactly {task_count} non-code contribution tasks that are:
1. SPECIFIC to this repository — reference actual docs, screens, languages, \
or sections you can infer from the README and file structure.
2. COMPLETABLE without any programming knowledge — no code, no PRs, \
no terminal commands.
3. DIFFERENT from every existing issue listed above.
4. Spread across different categories where possible.

Allowed categories: design | documentation | translation | community | \
marketing | research

Return a JSON array with exactly {task_count} objects. Each object must have \
these exact keys:
  "title"           — action statement, max 15 words, starts with a verb
  "description"     — exactly 2 sentences: what to do, then why it matters
  "category"        — one of the allowed categories above
  "difficulty"      — "beginner" | "intermediate" | "advanced"
  "estimated_hours" — 3 | 6 | 10  (integer)

Return ONLY the JSON array. No markdown fences, no prose, no explanation.\
"""


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_owner_repo(repo_url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.

    Args:
        repo_url: Full GitHub URL e.g. https://github.com/django/django

    Returns:
        (owner, repo_name) tuple

    Raises:
        ValueError: If the URL is not a recognisable GitHub repo URL.
    """
    url = repo_url.strip().rstrip("/")
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)$", url)
    if not match:
        raise ValueError(f"Not a valid GitHub repo URL: {repo_url!r}")
    return match.group(1), match.group(2)


def _validate_generated_task(raw: dict) -> Optional[dict]:
    """
    Validate and normalise a single task dict returned by Claude.

    Defensive — malformed fields are corrected rather than rejected so
    a single bad field doesn't discard an otherwise good task.

    Returns:
        Normalised task dict, or None if the task is unsalvageable.
    """
    if not isinstance(raw, dict):
        return None

    title = str(raw.get("title", "")).strip()
    description = str(raw.get("description", "")).strip()
    category = str(raw.get("category", "")).strip().lower()
    difficulty = str(raw.get("difficulty", "beginner")).strip().lower()
    estimated_hours = raw.get("estimated_hours", 6)

    # Title and description are required
    if not title or not description:
        return None

    # Clamp to valid enum values
    if category not in VALID_CATEGORIES:
        category = "documentation"
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = "beginner"
    try:
        estimated_hours = int(estimated_hours)
    except (TypeError, ValueError):
        estimated_hours = 6
    if estimated_hours not in VALID_HOURS:
        estimated_hours = 6

    return {
        "title": title[:300],
        "description": description,
        "category": category,
        "difficulty": difficulty,
        "estimated_hours": estimated_hours,
    }


def _call_claude(prompt: str) -> Optional[list[dict]]:
    """
    Send the generation prompt to Claude and parse the JSON response.

    Uses a single non-streaming call. max_tokens=2000 is generous enough
    for 6 tasks (≈ 80 tokens each) while protecting against runaway output.

    Returns:
        List of validated task dicts, or None if generation or parsing failed.
    """
    if not config.ANTHROPIC_API_KEY:
        logger.error(
            "ai_task_generator: ANTHROPIC_API_KEY is not set — "
            "task generation is disabled. Add the key to your environment."
        )
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.error(
            "ai_task_generator: error calling Claude",
            extra={"error": str(e)},
        )
        return None

    raw_text = message.content[0].text.strip() if message.content else ""
    if not raw_text:
        logger.warning("ai_task_generator: Claude returned empty response")
        return None

    # Strip markdown fences if Claude added them despite instructions
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip().strip("`")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract a JSON array with a permissive regex
        array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
            except json.JSONDecodeError:
                logger.warning("ai_task_generator: could not parse Claude JSON response")
                return None
        else:
            logger.warning("ai_task_generator: no JSON array found in Claude response")
            return None

    if not isinstance(parsed, list):
        logger.warning("ai_task_generator: Claude response was not a JSON array")
        return None

    tasks = []
    for item in parsed:
        validated = _validate_generated_task(item)
        if validated:
            tasks.append(validated)

    logger.info(
        "ai_task_generator: Claude generated tasks",
        extra={"valid_tasks": len(tasks), "raw_items": len(parsed)},
    )
    return tasks if tasks else None


# ── Public API ─────────────────────────────────────────────────────────────────

def preview_tasks_for_repo(repo_url: str) -> dict:
    """
    Fetch repository context and generate non-code contribution tasks via Claude.

    Does NOT save anything to the database.  Returns the generated tasks and
    the resolved repo name so the frontend can display a preview immediately.

    Validation flow:
      1. Parse owner/repo from URL
      2. Fetch repo metadata — reject private, archived, or non-OSS repos
      3. Fetch README — reject if completely absent
      4. Fetch top-level file structure and first page of open issues
      5. Build prompt and call Claude
      6. Return validated tasks

    Args:
        repo_url: Full GitHub repository URL

    Returns:
        Dict: { repo_name: str, tasks: list[dict] }

    Raises:
        ValueError: If the repo URL is invalid, repo is private/archived/
                    unlicensed, or the README is missing.
        RuntimeError: If Claude generation fails.
    """
    # ── Step 1: parse URL ─────────────────────────────────────────────────────
    owner, repo_name = _parse_owner_repo(repo_url)

    # ── Step 2: fetch and validate repo metadata ──────────────────────────────
    repo_data = github_client.get_repo(owner, repo_name)
    if not repo_data:
        raise ValueError(
            "Could not fetch repository information. "
            "Check that the URL is correct and the repository is public."
        )

    if repo_data.get("private", False):
        raise ValueError("This repository is private. Nocos only works with public repositories.")

    if repo_data.get("archived", False):
        raise ValueError("This repository is archived and no longer accepts contributions.")

    license_obj = repo_data.get("license") or {}
    spdx_id: Optional[str] = license_obj.get("spdx_id") if license_obj else None
    if not spdx_id or spdx_id == "NOASSERTION" or spdx_id not in OPEN_SOURCE_LICENSES:
        raise ValueError(
            "This repository does not have a recognised open source license. "
            "Nocos only lists repositories with approved OSI/Creative Commons licenses."
        )

    # ── Step 3: fetch README — required for meaningful task generation ────────
    readme_text = github_client.get_readme(owner, repo_name)
    if readme_text is None:
        raise ValueError(
            "This repository has no README. "
            "A README is required for Claude to understand the project context."
        )

    # ── Step 4: supporting context ────────────────────────────────────────────
    file_names = github_client.get_repo_contents(owner, repo_name)
    open_issues = github_client.get_open_issues(owner, repo_name, per_page=20)

    # Build human-readable summaries — never log raw bodies
    file_structure_str = ", ".join(file_names[:40]) if file_names else "(not available)"

    # Only include issue titles, never bodies, to avoid logging sensitive content
    existing_issue_titles = [
        f"- {issue.get('title', '')}"
        for issue in open_issues
        if not issue.get("pull_request")  # exclude PRs
    ][:20]
    existing_issues_str = (
        "\n".join(existing_issue_titles) if existing_issue_titles else "(no open issues)"
    )

    # Build context strings from metadata
    topics = ", ".join(repo_data.get("topics") or []) or "(none)"
    language = repo_data.get("language") or "not specified"
    stars = repo_data.get("stargazers_count", 0)
    description = repo_data.get("description") or "(no description)"
    license_name = license_obj.get("name", spdx_id) if license_obj else spdx_id
    full_repo_name = repo_data.get("full_name", f"{owner}/{repo_name}")

    # ── Step 5: build prompt and call Claude ──────────────────────────────────
    prompt = _GENERATION_PROMPT.format(
        task_count=TASKS_PER_REPO,
        repo_name=full_repo_name,
        description=description,
        language=language,
        stars=stars,
        topics=topics,
        license=license_name,
        file_structure=file_structure_str,
        readme=readme_text[:3000],  # Cap at 3000 chars for prompt safety
        existing_issues=existing_issues_str,
    )

    tasks = _call_claude(prompt)
    if not tasks:
        raise RuntimeError(
            "Task generation failed. Claude could not produce valid tasks for this repository. "
            "Please try again or try a different repository."
        )

    logger.info(
        "ai_task_generator: preview complete",
        extra={"owner": owner, "repo": repo_name, "task_count": len(tasks)},
    )

    return {
        "repo_name": full_repo_name,
        "tasks": tasks,
    }


def publish_tasks_for_repo(
    tasks: list[dict],
    repo_url: str,
    db,  # SQLAlchemy Session — imported lazily to avoid circular imports
) -> dict:
    """
    Save previously generated tasks to the database.

    Only called when the user explicitly clicks Publish.  The tasks list comes
    from the preview response — the server validates each task again before
    saving to guard against tampered requests.

    Deduplication: tasks with the same title + project are silently skipped
    so re-publishing is safe.

    Args:
        tasks:    List of task dicts from the preview response
        repo_url: The GitHub repo URL (used to look up or create the project)
        db:       Active SQLAlchemy session

    Returns:
        Dict: { saved_count: int, tasks: list[{id, title}] }

    Raises:
        ValueError: If the repo URL is invalid or repo cannot be fetched.
    """
    from models.project import Project
    from models.task import Task
    from services.sync import calculate_activity_status
    from datetime import datetime, timezone

    owner, repo_name = _parse_owner_repo(repo_url)

    # ── Upsert the project ────────────────────────────────────────────────────
    project = (
        db.query(Project)
        .filter(Project.github_owner == owner, Project.github_repo == repo_name)
        .first()
    )

    if project is None:
        repo_data = github_client.get_repo(owner, repo_name)
        if not repo_data:
            raise ValueError(
                "Could not fetch repository information while saving tasks."
            )
        last_commit_raw = github_client.get_last_commit_date(owner, repo_name)
        last_commit_date = None
        if last_commit_raw:
            try:
                from datetime import datetime
                last_commit_date = datetime.fromisoformat(
                    last_commit_raw.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        status, score = calculate_activity_status(last_commit_date)
        project = Project(
            name=repo_data.get("full_name", f"{owner}/{repo_name}"),
            github_url=repo_data.get("html_url", repo_url),
            github_owner=owner,
            github_repo=repo_name,
            description=repo_data.get("description") or "",
            website_url=repo_data.get("homepage") or None,
            avatar_url=repo_data.get("owner", {}).get("avatar_url", ""),
            social_links={"github": f"https://github.com/{owner}/{repo_name}"},
            activity_score=score,
            activity_status=status,
            last_commit_date=last_commit_date,
            is_active=True,
        )
        db.add(project)
        db.flush()  # Populate project.id before inserting tasks
        logger.info(
            "ai_task_generator: new project created during publish",
            extra={"owner": owner, "repo": repo_name},
        )

    # ── Save tasks ────────────────────────────────────────────────────────────
    saved = []
    skipped = 0

    # Category → contribution_type_enum mapping
    _CATEGORY_TO_TYPE = {
        "design": "design",
        "documentation": "documentation",
        "translation": "translation",
        "community": "community",
        "marketing": "marketing",
        "research": "research",
    }

    for raw_task in tasks:
        validated = _validate_generated_task(raw_task)
        if not validated:
            skipped += 1
            continue

        # Deduplication: skip if same title already exists for this project
        existing = (
            db.query(Task)
            .filter(
                Task.project_id == project.id,
                Task.title == validated["title"],
            )
            .first()
        )
        if existing:
            skipped += 1
            logger.info(
                "ai_task_generator: duplicate task skipped",
                extra={"title": validated["title"][:60], "project_id": str(project.id)},
            )
            continue

        contribution_type = _CATEGORY_TO_TYPE.get(validated["category"], "other")

        task = Task(
            project_id=project.id,
            title=validated["title"],
            ai_title=None,  # Title is already clean — no further rewriting needed
            description_original=None,  # No original GitHub body for AI-generated tasks
            description_display=validated["description"],
            is_ai_generated=True,       # Description is AI-authored
            labels=[validated["category"]],
            contribution_type=contribution_type,
            is_paid=False,
            is_bounty=False,
            bounty_amount=None,
            difficulty=validated["difficulty"],
            source="ai_generated",      # Distinct from github_scrape / manual_post
            github_issue_url=repo_url,  # Links back to the repo, not a specific issue
            github_created_at=None,
            is_active=True,
            review_status="approved",   # AI generator tasks are immediately visible
        )
        db.add(task)
        db.flush()  # Populate task.id before appending to saved list
        saved.append({"id": str(task.id), "title": validated["title"]})

    db.commit()

    logger.info(
        "ai_task_generator: publish complete",
        extra={
            "owner": owner,
            "repo": repo_name,
            "saved": len(saved),
            "skipped": skipped,
        },
    )

    return {
        "saved_count": len(saved),
        "tasks": saved,
    }
