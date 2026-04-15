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
 *   < 1 hour  → "X minutes ago"
 *   < 24 hrs  → "X hours ago"
 *   < 7 days  → "X days ago"
 *   < 4 weeks → "X weeks ago"
 *   otherwise → "X months ago"
 *
 * @param dateString - ISO 8601 datetime string (e.g. "2024-03-15T10:30:00Z")
 * @returns Human-readable relative time string
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  if (diffMinutes < 60) {
    return diffMinutes <= 1 ? "1 minute ago" : `${diffMinutes} minutes ago`;
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 24) {
    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  }

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 7) {
    return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
  }

  const diffWeeks = Math.floor(diffDays / 7);
  if (diffWeeks < 4) {
    return diffWeeks === 1 ? "1 week ago" : `${diffWeeks} weeks ago`;
  }

  const diffMonths = Math.floor(diffDays / 30);
  return diffMonths === 1 ? "1 month ago" : `${diffMonths} months ago`;
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
