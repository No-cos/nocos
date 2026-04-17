# services/issue_finder/bounty_detector.py
# Detects real-money bounties on GitHub issues.
#
# Bounty platforms (Algora, IssueHunt, Bountysource, etc.) signal a reward
# either by attaching a special label or by posting a structured bot comment
# in the issue body. This module checks all three surfaces — labels, title,
# and body — and returns both a boolean flag and the parsed USD amount.
#
# Amount precision: stored in USD cents (integer) so $50 → 5000 and $1.50 → 150.
# This avoids float rounding issues in the DB while keeping the value exact.
#
# False-positive strategy:
#   Dollar amounts in the body alone are NOT treated as a bounty signal.
#   Too many non-bounty issues mention prices ("API costs $20/month"),
#   costs, or budgets. We only trust body amounts when a stronger signal
#   (label, platform keyword, or title amount) is already present.

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Label signals ──────────────────────────────────────────────────────────────
# GitHub label names that indicate a real-money reward is attached.
BOUNTY_LABELS: frozenset[str] = frozenset({
    "bounty",
    "algora",
    "issuehunt",
    "bountysource",
    "💰",
    "$",
    "reward",
    "prize",
    "funded",
    "funding",
    "bounty-available",
    "reward-available",
    "has-bounty",
    "has bounty",
})

# ── Amount extraction regexes ──────────────────────────────────────────────────

# Matches $50, $100.00, $1,000, $ 50 (optional space after $)
_DOLLAR_RE = re.compile(
    r"\$\s*(\d{1,6}(?:[,\d]{0,3})*(?:\.\d{1,2})?)"
)

# Matches "100 USD", "50 dollars", "25 dollar" (word-boundary anchored)
_USD_WORD_RE = re.compile(
    r"\b(\d{1,6})\s*(?:USD|dollars?)\b",
    re.IGNORECASE,
)


def _extract_cents(text: str) -> Optional[int]:
    """
    Return the largest USD amount found in *text*, converted to cents.

    Tries $-prefix patterns first, then "N USD" / "N dollars" patterns.
    Returns None if no parseable amount is found.

    Args:
        text: Raw text to search (title, body, or both concatenated)

    Returns:
        Integer cent amount (e.g. 5000 for $50), or None.
    """
    best: Optional[int] = None

    for raw in _DOLLAR_RE.findall(text):
        try:
            # Remove thousand-separator commas before parsing
            cents = int(round(float(raw.replace(",", "")) * 100))
            if cents > 0 and (best is None or cents > best):
                best = cents
        except ValueError:
            pass

    if best is None:
        for raw in _USD_WORD_RE.findall(text):
            try:
                cents = int(raw) * 100
                if cents > 0:
                    return cents
            except ValueError:
                pass

    return best


def detect_bounty(issue: dict) -> tuple[bool, Optional[int]]:
    """
    Return (is_bounty, bounty_amount_cents) for a structured issue dict.

    Detection heuristics applied in order of reliability:

    1. **Label** — issue has a bounty-specific label (most reliable;
       maintainers explicitly tag bounty issues).
    2. **Platform keyword** — title or body contains "algora", "issuehunt",
       "💰", or "💸" (bounty-bot comments always include these).
    3. **Reward keyword** — title or body contains "bounty", "[reward]",
       "[bounty]", or "[prize]".
    4. **Dollar amount in the title** — e.g. "$50 fix login bug" or
       "[$100] improve docs". Title amounts are trusted; body amounts alone
       are not (too many false positives from pricing/cost mentions).

    For heuristics 1–4 the full text (title + body) is scanned for an
    amount to populate bounty_amount_cents.

    Args:
        issue: Structured issue dict with "labels", "title", and "body" keys

    Returns:
        Tuple of (is_bounty: bool, bounty_amount_cents: int | None).
        bounty_amount_cents is None when no dollar amount could be parsed.
    """
    labels_lower = {lbl.lower() for lbl in issue.get("labels", [])}
    title: str = issue.get("title") or ""
    body: str = issue.get("body") or ""
    title_lower = title.lower()
    body_lower = body.lower()
    full_text = f"{title} {body}"

    # ── 1. Bounty label ────────────────────────────────────────────────────────
    if labels_lower & BOUNTY_LABELS:
        return True, _extract_cents(full_text)

    # ── 2. Known bounty platform keywords ─────────────────────────────────────
    # Algora and IssueHunt post structured bot comments; their names / emoji
    # appear reliably in the issue body when a bounty is active.
    if any(
        kw in title_lower or kw in body_lower
        for kw in ("algora", "issuehunt", "bountysource", "💰", "💸")
    ):
        return True, _extract_cents(full_text)

    # ── 3. Generic bounty/reward keywords ─────────────────────────────────────
    if any(
        kw in title_lower or kw in body_lower
        for kw in ("bounty", "[reward]", "[bounty]", "[prize]")
    ):
        return True, _extract_cents(full_text)

    # ── 4. Dollar amount explicitly in the issue title ─────────────────────────
    if _DOLLAR_RE.search(title):
        amount = _extract_cents(title)
        if amount is not None:
            return True, amount

    return False, None
