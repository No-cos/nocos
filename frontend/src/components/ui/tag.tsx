/**
 * Tag component — contribution type label pill.
 *
 * Design system rule (features.md §2): tags use a colored border/outline
 * only. Fill and text stay neutral so the design stays clean while
 * contribution types remain identifiable at a glance.
 *
 * @param type       - Contribution type key (e.g. "design", "documentation").
 *                     Determines the border color.
 * @param label      - Display text. Falls back to a formatted version of `type`
 *                     if not provided.
 * @param size       - "sm" (default) for grid cards, "md" for filter bar pills.
 * @param selected   - Renders the selected state.
 * @param onClick    - Makes the tag interactive (filter bar usage).
 * @param filterMode - When true, uses neutral border by default and
 *                     var(--color-cta-primary) only when selected.
 *                     Individual type colors are suppressed.
 *                     Defaults to false so marquee/card tags are unaffected.
 */

import { getTagColor, formatContributionType } from "@/lib/utils";

export interface TagProps {
  type: string;
  label?: string;
  size?: "sm" | "md";
  selected?: boolean;
  onClick?: () => void;
  className?: string;
  filterMode?: boolean;
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
  filterMode = false,
}: TagProps) {
  const displayLabel = label ?? formatContributionType(type);

  const sizeStyles =
    size === "md"
      ? { fontSize: "13px", padding: "5px 14px" }
      : { fontSize: "12px", padding: "3px 10px" };

  const borderColor = filterMode
    ? selected
      ? "var(--color-cta-primary)"
      : "var(--color-border)"
    : getTagColor(type);

  // Active fill: applied when an interactive tag (has onClick) is selected.
  // Purple background + white text signals the selected state clearly.
  // Issue card tags never have onClick so they are never affected by this.
  const isActiveSelected = !!onClick && selected;

  const baseStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    backgroundColor: isActiveSelected ? "var(--color-cta-primary)" : "var(--color-surface)",
    color: isActiveSelected ? "#ffffff" : "var(--color-text-primary)",
    border: `1.5px solid ${isActiveSelected ? "var(--color-cta-primary)" : borderColor}`,
    borderRadius: "999px",
    fontFamily: "'Inter', sans-serif",
    fontWeight: 500,
    lineHeight: 1.4,
    whiteSpace: "nowrap",
    transition: "background-color 150ms ease, border-color 150ms ease, color 150ms ease",
    cursor: onClick ? "pointer" : "default",
    opacity: filterMode ? 1 : selected ? 1 : 0.85,
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
