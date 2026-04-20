# services/ai/description.py
# Anthropic client for AI enrichment of GitHub issues.
# Produces two outputs per issue in a single API call:
#   - ai_title:           plain, action-oriented rewrite of the GitHub title
#   - description_display: 2-3 sentence contributor-facing description
#
# Cost control measures:
#   - One Claude call per issue covers both title and description
#   - Generation happens once on first import
#   - Regenerated only if the original issue body changes on GitHub
#   - Output capped by max_tokens — never blocks the sync job on failure

import json
import logging
import re
from typing import Optional

import anthropic

from config import config
from services.retry import retry_call

logger = logging.getLogger(__name__)

# The model to use for enrichment.
# claude-sonnet-4-5 balances quality and cost for short-form generation.
CLAUDE_MODEL = "claude-sonnet-4-5"

# Minimum word count for an existing description to be considered usable.
# Below this threshold we generate a replacement with Claude.
MIN_DESCRIPTION_WORDS = 20

# Fallback strings shown when generation fails — never a blank card.
FALLBACK_DESCRIPTION = "Visit GitHub for full details on this task."
FALLBACK_TITLE = None  # None means the original GitHub title is used as-is

# ─── Enrichment prompt (title + description in one call) ──────────────────────
#
# Returns a JSON object so parsing is deterministic.
# Title: action-oriented, max 12 words, plain English, no jargon.
# Description: 2-3 sentences, starts with what the contributor will DO,
#              mentions the skill required, no code references.
ENRICHMENT_PROMPT_TEMPLATE = """You are helping non-technical contributors discover open source tasks.

Given this GitHub issue:
- Repository: {repo_name} — {repo_description}
- Original title: {issue_title}
- Labels: {labels}
- Issue body: {body}
- Top comments: {first_comments}

Return a JSON object with exactly two keys:

"title": Rewrite the issue title as a plain, action-oriented phrase (maximum 12 words) that a designer, writer, or researcher can immediately understand. Remove all technical jargon, version numbers, and code references. Start with an active verb when possible.

"description": Write 2-3 sentences describing what the contributor will actually do. Start with "You will..." or "This task involves...". Mention the specific skill required (e.g. writing, design, translation, research). Use plain English — no GitHub jargon, no code references, no mention of pull requests or commits. Write for someone discovering open source for the first time.

Examples of good output:
{{"title": "Help translate the app into new languages for the upcoming release", "description": "You will translate text strings in the app into your language, making it accessible to more people around the world. This task requires fluency in both English and the target language. No technical skills are needed — just careful, accurate translation."}}
{{"title": "Design an empty state screen for the dashboard", "description": "You will design a friendly screen shown to new users who have no data yet. This task requires visual design skills and an eye for user experience. The goal is to make the app feel welcoming rather than empty."}}

Return only the JSON object — no other text, no markdown code fences."""


def strip_markdown(text: str) -> str:
    """
    Remove markdown and HTML formatting from a string.

    Used to get an accurate word count from issue bodies — "**bold**" should
    count as one word, not three. Stripping before counting prevents short but
    heavily formatted issues from being incorrectly flagged as needing AI help.

    Args:
        text: Raw markdown or HTML string

    Returns:
        Plain text with formatting stripped.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove markdown links — keep the label text, drop the URL
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove markdown headers, bold, italic, code blocks
    text = re.sub(r"[#*_`~>]+", "", text)
    # Collapse multiple whitespace into single spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def needs_ai_description(body: Optional[str]) -> bool:
    """
    Determine whether an issue needs an AI-generated description.

    Returns True when:
    - The issue body is None or empty
    - The body has fewer than MIN_DESCRIPTION_WORDS words after stripping markdown

    Args:
        body: Raw GitHub issue body (may be None)

    Returns:
        True if AI generation is needed.
    """
    if not body:
        return True

    word_count = len(strip_markdown(body).split())
    return word_count < MIN_DESCRIPTION_WORDS


def generate_enrichment(
    body: Optional[str],
    repo_name: str,
    repo_description: str,
    issue_title: str,
    labels: list,
    first_comments: list,
) -> dict:
    """
    Generate both an AI title and a plain-English description in one Claude call.

    Always rewrites the title. Only generates a description when the original
    body is missing or too short (< MIN_DESCRIPTION_WORDS words). If the body
    is sufficient, description_display is set from the original body and
    is_ai_generated is False, but ai_title is still produced.

    Args:
        body:             Raw GitHub issue body (may be None)
        repo_name:        Repository full name (e.g. "chaoss/augur")
        repo_description: Short description from the GitHub repo description field
        issue_title:      Original GitHub issue title
        labels:           List of GitHub label name strings
        first_comments:   Up to 3 comment body strings for extra context

    Returns:
        Dict with keys:
          ai_title (str | None):       AI-rewritten title, None on failure
          description_display (str):   Display description (AI or original body)
          is_ai_generated (bool):      True if description_display came from Claude
    """
    need_description = needs_ai_description(body)

    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set — skipping enrichment")
        return {
            "ai_title": None,
            "description_display": body if not need_description else FALLBACK_DESCRIPTION,
            "is_ai_generated": False,
        }

    prompt = ENRICHMENT_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        repo_description=repo_description or "No description available",
        issue_title=issue_title,
        labels=", ".join(labels) if labels else "none",
        body=strip_markdown(body)[:800] if body else "No body provided",
        first_comments=(
            "\n".join(f"- {c[:300]}" for c in first_comments)
            if first_comments
            else "No comments yet"
        ),
    )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx = {"repo": repo_name, "issue_title": issue_title[:60]}

    def _call_claude() -> str:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,  # title ~15 tokens + description ~120 tokens + JSON overhead
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    raw = retry_call(_call_claude, fallback=None, context=ctx, log=logger)

    if raw is None:
        # All retries exhausted — return safe fallbacks
        return {
            "ai_title": None,
            "description_display": body if not need_description else FALLBACK_DESCRIPTION,
            "is_ai_generated": False,
        }

    # Parse the JSON response — be defensive, Claude occasionally adds prose
    ai_title: Optional[str] = None
    generated_description: Optional[str] = None
    try:
        # Strip any accidental markdown fences before parsing
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        parsed = json.loads(cleaned)
        ai_title = parsed.get("title") or None
        generated_description = parsed.get("description") or None
    except (json.JSONDecodeError, AttributeError):
        logger.warning(
            "Failed to parse enrichment JSON — falling back",
            extra={"repo": repo_name, "raw_preview": raw[:120]},
        )

    # Decide description_display
    if need_description:
        description_display = generated_description or FALLBACK_DESCRIPTION
        is_ai_generated = bool(generated_description)
    else:
        # Original body is long enough — use it, even if JSON parse failed
        description_display = body  # type: ignore[assignment]
        is_ai_generated = False

    logger.info(
        "AI enrichment complete",
        extra={
            "repo": repo_name,
            "issue_title": issue_title[:60],
            "ai_title_generated": ai_title is not None,
            "description_ai": is_ai_generated,
        },
    )

    return {
        "ai_title": ai_title,
        "description_display": description_display,
        "is_ai_generated": is_ai_generated,
    }


# ─── Legacy helpers (kept for backward compatibility) ─────────────────────────

def generate_description(
    repo_name: str,
    repo_description: str,
    issue_title: str,
    labels: list,
    first_comments: list,
) -> str:
    """
    Generate a plain-English description only (no title rewrite).
    Kept for backward compatibility with the description backfill path.
    New code should call generate_enrichment() instead.
    """
    result = generate_enrichment(
        body=None,  # force description generation
        repo_name=repo_name,
        repo_description=repo_description,
        issue_title=issue_title,
        labels=labels,
        first_comments=first_comments,
    )
    return result["description_display"]


def process_issue_description(
    body: Optional[str],
    repo_name: str,
    repo_description: str,
    issue_title: str,
    labels: list,
    first_comments: list,
) -> tuple[str, bool]:
    """
    Decide whether to use the original description or generate one with Claude.
    Kept for backward compatibility — new code calls generate_enrichment().

    Returns:
        Tuple of (description_display: str, is_ai_generated: bool)
    """
    result = generate_enrichment(
        body=body,
        repo_name=repo_name,
        repo_description=repo_description,
        issue_title=issue_title,
        labels=labels,
        first_comments=first_comments,
    )
    return result["description_display"], result["is_ai_generated"]
