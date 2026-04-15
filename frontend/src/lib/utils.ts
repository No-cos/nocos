// utils.ts
// General-purpose utility functions for the Nocos frontend.
// Small helpers that don't belong to any specific component or feature.

/**
 * Formats a UTC datetime string into a human-readable relative time label.
 * Used for activity indicators (e.g. "last commit 3 days ago").
 *
 * @param dateString - ISO 8601 datetime string
 * @returns Relative time string (e.g. "3 days ago", "2 months ago")
 */
export function relativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Converts an ISO 8601 date string to a short human-readable relative time.
 * Used on issue cards and the task detail page to show when an issue was posted.
 *
 * Resolutions (in order of precedence):
 *   < 1 minute → "just now"
 *   1–59 min   → "X minutes ago"
 *   1–23 hrs   → "X hours ago"
 *   1–6 days   → "X days ago"
 *   1–3 weeks  → "X weeks ago"
 *   ≥ 4 weeks  → "4 weeks ago"  (hard cap — issues this old are filtered out)
 *
 * Each threshold floors the value and only uses that unit when the result
 * is ≥ 1, so "0 X ago" can never appear.
 *
 * @param dateString - ISO 8601 datetime string (e.g. "2024-03-15T10:30:00Z")
 * @returns Human-readable relative time string
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = Math.max(0, now.getTime() - date.getTime());

  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  if (diffMinutes < 1) return "just now";

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) {
    return diffMinutes === 1 ? "1 minute ago" : `${diffMinutes} minutes ago`;
  }

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 1) {
    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  }

  const diffWeeks = Math.floor(diffDays / 7);
  if (diffWeeks < 1) {
    return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
  }

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 1) {
    // 1–3 weeks (7–27 days)
    return diffWeeks === 1 ? "1 week ago" : `${diffWeeks} weeks ago`;
  }

  // ≥ 4 weeks: cap at "4 weeks ago".
  // Issues this old are filtered out before reaching the display layer, so
  // this branch only fires in edge cases (e.g. clock skew, mock data).
  return "4 weeks ago";
}

/**
 * Returns the CSS variable name for a contribution type's tag border color.
 * Tags use colored borders only — the color itself is defined in globals.css.
 *
 * @param type - Contribution type string (e.g. "design", "documentation")
 * @returns CSS variable string (e.g. "var(--tag-design)")
 */
export function getTagColor(_type: string): string {
  return "#C6C9D3";
}

/**
 * Returns the activity status color token for a given status.
 * Used for the colored dot on issue cards and the detail page.
 *
 * @param status - "active" | "slow" | "inactive"
 * @returns CSS variable string for the status color
 */
export function getActivityColor(
  status: "active" | "slow" | "inactive"
): string {
  const colorMap = {
    active: "var(--color-status-active)",
    slow: "var(--color-status-slow)",
    inactive: "var(--color-status-inactive)",
  };
  return colorMap[status];
}

/**
 * Truncates a string to a maximum number of words.
 * Used for card description previews.
 *
 * @param text - The string to truncate
 * @param maxWords - Maximum number of words to show
 * @returns Truncated string with ellipsis if needed
 */
export function truncateWords(text: string, maxWords: number): string {
  const words = text.trim().split(/\s+/);
  if (words.length <= maxWords) return text;
  return words.slice(0, maxWords).join(" ") + "…";
}

/**
 * Validates an email address format.
 * Used in the subscribe form before submitting to the API.
 *
 * @param email - The email string to validate
 * @returns true if the email format is valid
 */
export function isValidEmail(email: string): boolean {
  // Standard email regex — good enough for UI validation before server-side check
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Formats a contribution type enum value into a human-readable label.
 * e.g. "pr_review" → "PR Review", "data_analytics" → "Data Analytics"
 *
 * @param type - Raw contribution type string from the API
 * @returns Formatted display label
 */
export function formatContributionType(type: string): string {
  const labelMap: Record<string, string> = {
    design: "Design",
    documentation: "Documentation",
    pr_review: "PR Review",
    data_analytics: "Data Analytics",
    translation: "Translation",
    research: "Research",
    community: "Community Management",
    marketing: "Marketing",
    social_media: "Social Media",
    project_management: "Project Management",
    other: "Other",
  };
  return labelMap[type] ?? type;
}
