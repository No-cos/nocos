# services/ai/description.py
# Anthropic client for generating plain-English issue descriptions.
# Called when a GitHub issue has no body, or a body shorter than 20 words
# after stripping markdown — as defined in features.md Section 5.
#
# Cost control measures (features.md Section 5):
#   - Generation happens once per issue (on first import)
#   - Regenerated only if the original issue body changes on GitHub
#   - Output capped at 60 words via the prompt
#   - Failed generation returns a safe fallback — never blocks the sync job

import logging
import re
from typing import Optional

import anthropic

from config import config

logger = logging.getLogger(__name__)

# The model to use for description generation.
# claude-sonnet-4-5 balances quality and cost for short-form generation.
CLAUDE_MODEL = "claude-sonnet-4-5"

# Minimum word count for an existing description to be considered usable.
# Below this threshold, we generate a replacement with Claude.
MIN_DESCRIPTION_WORDS = 20

# Fallback string shown when generation fails — never a blank card.
FALLBACK_DESCRIPTION = "Visit GitHub for full details on this task."

# Prompt template — fills in repo, issue, labels, and top comments.
# Written to produce plain English for non-technical readers.
DESCRIPTION_PROMPT_TEMPLATE = """You are helping non-technical contributors understand open source tasks.

Given this GitHub issue:
- Repository: {repo_name} — {repo_description}
- Issue title: {issue_title}
- Labels: {labels}
- Top comments: {first_comments}

Write a clear, plain-English description (maximum 60 words) of what this task involves. Write for someone with no coding background — a designer, writer, or researcher. Do not mention GitHub, pull requests, or technical implementation details. Focus on what the person will actually be doing."""


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
    - The body has fewer than 20 words after stripping markdown

    Args:
        body: Raw GitHub issue body (may be None)

    Returns:
        True if AI generation is needed.
    """
    if not body:
        return True

    word_count = len(strip_markdown(body).split())
    # Below 20 words the description is too thin for a non-technical reader
    return word_count < MIN_DESCRIPTION_WORDS


def generate_description(
    repo_name: str,
    repo_description: str,
    issue_title: str,
    labels: list,
    first_comments: list,
) -> str:
    """
    Generate a plain-English description for a GitHub issue using Claude Sonnet.

    This is called when an issue has no body, or a body shorter than 20 words.
    The goal is to make the issue readable for non-technical contributors who
    may not understand GitHub-specific language or developer jargon.

    The Anthropic client is initialised inline so the API key is read after
    the app config has been validated at startup.

    Args:
        repo_name:        Repository full name (e.g. "chaoss/augur")
        repo_description: Short description from the GitHub repo description field
        issue_title:      The issue title
        labels:           List of GitHub label name strings
        first_comments:   Up to 3 comment body strings for extra context

    Returns:
        A generated description capped at 60 words, or FALLBACK_DESCRIPTION
        if generation fails for any reason.
    """
    prompt = DESCRIPTION_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        repo_description=repo_description or "No description available",
        issue_title=issue_title,
        labels=", ".join(labels) if labels else "none",
        first_comments=(
            "\n".join(f"- {c}" for c in first_comments)
            if first_comments
            else "No comments yet"
        ),
    )

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=150,  # 60 words ≈ 80–100 tokens; 150 gives a safe buffer
            messages=[{"role": "user", "content": prompt}],
        )

        generated = message.content[0].text.strip()

        logger.info(
            "AI description generated",
            extra={
                "repo": repo_name,
                "issue_title": issue_title[:60],
                "word_count": len(generated.split()),
            },
        )
        return generated

    except anthropic.AuthenticationError:
        # Invalid API key — log clearly so it's obvious during setup
        logger.error(
            "Anthropic authentication failed — check ANTHROPIC_API_KEY in .env"
        )
        return FALLBACK_DESCRIPTION

    except anthropic.RateLimitError:
        # Anthropic rate limit hit — return fallback, the sync job continues
        logger.warning(
            "Anthropic rate limit reached — using fallback description",
            extra={"repo": repo_name},
        )
        return FALLBACK_DESCRIPTION

    except Exception as e:
        # Any other failure — log with full context but never crash the sync job
        logger.exception(
            "Unexpected error generating AI description",
            extra={"repo": repo_name, "issue_title": issue_title, "error": str(e)},
        )
        return FALLBACK_DESCRIPTION


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

    This is the main entry point called by the scraper for each issue.
    Returns a tuple so the caller knows whether to set is_ai_generated=True.

    Args:
        body:             Raw GitHub issue body (may be None)
        repo_name:        Repository full name
        repo_description: GitHub repo description
        issue_title:      Issue title
        labels:           GitHub label names
        first_comments:   Up to 3 comment strings for context

    Returns:
        Tuple of (description_display: str, is_ai_generated: bool)
    """
    if not needs_ai_description(body):
        # Original description is good enough — use it as-is
        return (body, False)  # type: ignore[return-value]

    # Original is missing or too short — generate with Claude
    generated = generate_description(
        repo_name=repo_name,
        repo_description=repo_description,
        issue_title=issue_title,
        labels=labels,
        first_comments=first_comments,
    )
    return (generated, True)
