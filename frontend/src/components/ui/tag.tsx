/**
 * Tag component — contribution type label pill.
 *
 * Design system rule (features.md §2): tags use a colored border/outline
 * only. Fill and text stay neutral so the design stays clean while
 * contribution types remain identifiable at a glance.
 *
 * @param type    - Contribution type key (e.g. "design", "documentation").
 *                  Determines the border color.
 * @param label   - Display text. Falls back to a formatted version of `type`
 *                  if not provided.
 * @param size    - "sm" (default) for grid cards, "md" for filter bar pills.
 * @param selected - Renders the selected state (slightly elevated border opacity).
 * @param onClick  - Makes the tag interactive (filter bar usage).
 */

import { getTagColor, formatContributionType } from "@/lib/utils";

export interface TagProps {
  type: string;
  label?: string;
  size?: "sm" | "md";
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}

// All 13 contribution types — used by the marquee and filter bar.
export const ALL_CONTRIBUTION_TYPES = [
  "design",
  "documentation",
  "pr_review",
  "data_analytics",
  "translation",
  "research",
  "community",
  "marketing",
  "social_media",
  "project_management",
  "hacktoberfest",
  "paid",
  "beginner",
] as const;

export function Tag({
  type,
  label,
  size = "sm",
  selected = false,
  onClick,
  className,
}: TagProps) {
  const borderColor = getTagColor(type);
  const displayLabel = label ?? formatContributionType(type);

  const sizeStyles =
    size === "md"
      ? { fontSize: "13px", padding: "5px 14px" }
      : { fontSize: "12px", padding: "3px 10px" };

  const baseStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    backgroundColor: "var(--color-surface)",
    color: "var(--color-text-primary)",
    border: `1.5px solid ${borderColor}`,
    borderRadius: "999px",
    fontFamily: "'Inter', sans-serif",
    fontWeight: 500,
    lineHeight: 1.4,
    whiteSpace: "nowrap",
    transition: "opacity 150ms ease, transform 150ms ease",
    cursor: onClick ? "pointer" : "default",
    // Selected state: elevated opacity on the border to indicate active filter
    opacity: selected ? 1 : 0.85,
    userSelect: "none",
    ...sizeStyles,
  };

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        style={baseStyle}
        className={className}
        aria-pressed={selected}
      >
        {displayLabel}
      </button>
    );
  }

  return (
    <span style={baseStyle} className={className}>
      {displayLabel}
    </span>
  );
}
