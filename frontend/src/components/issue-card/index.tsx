"use client";

/**
 * IssueCard component — displays a single issue in the discovery grid.
 *
 * Layout:
 * - Top: project avatar (32×32 circle) + project name
 * - Title: Plus Jakarta Sans, medium weight, 2-line clamp
 * - Tags: max 3 visible, "+N" overflow badge if more
 * - Description: Inter, secondary text color, 3-line clamp
 * - Bottom row left:  activity status dot + label
 * - Bottom row right: ✨ badge if is_ai_generated
 *
 * Hover: card lifts 2px, border becomes visible.
 * All colours via CSS variables — no hardcoded hex values.
 *
 * @param issue   - Issue data from the Nocos API
 * @param onClick - Called when the card is clicked (navigate to /tasks/[id])
 */

import Image from "next/image";
import { Tag } from "@/components/ui/tag";
import { getActivityColor, formatContributionType } from "@/lib/utils";
import type { IssueCardProps } from "./types";

// Max tags shown on a card — remainder shown as "+N" badge
const MAX_VISIBLE_TAGS = 3;

// Activity status labels used in the bottom row
const ACTIVITY_LABELS: Record<string, string> = {
  active: "Active",
  slow: "Slow",
  inactive: "Inactive",
};

export function IssueCard({ issue, onClick }: IssueCardProps) {
  // We cap tags at 3 on the card to avoid visual clutter.
  // The full tag list is shown on the detail page.
  const visibleTags = [issue.contribution_type, ...issue.labels].slice(
    0,
    MAX_VISIBLE_TAGS
  );
  const hiddenTagCount =
    [issue.contribution_type, ...issue.labels].length - visibleTags.length;

  const activityColor = getActivityColor(issue.project.activity_status);
  const activityLabel =
    ACTIVITY_LABELS[issue.project.activity_status] ?? issue.project.activity_status;

  return (
    <article
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        // Allow keyboard activation for accessibility (SKILLS.md §10)
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`${issue.title} — ${formatContributionType(issue.contribution_type)}`}
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        boxShadow: "var(--card-shadow)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        // Fixed height ensures every card in the grid is the same size
        // regardless of how long the title or description content is.
        height: "320px",
        // alignSelf: "start" prevents CSS Grid's default "stretch" behaviour
        // from overriding the explicit height and making this card as tall as
        // the tallest sibling in the same grid row.
        alignSelf: "start",
        // overflow: hidden clips any child content that still exceeds the box,
        // preventing visual bleed below the card border.
        overflow: "hidden",
        cursor: onClick ? "pointer" : "default",
        transition: "transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease",
        outline: "none",
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.transform = "translateY(-2px)";
        el.style.borderColor = "var(--color-text-secondary)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.transform = "translateY(0)";
        el.style.borderColor = "var(--color-border)";
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = "2px solid var(--color-cta-primary)";
        e.currentTarget.style.outlineOffset = "2px";
      }}
      onBlur={(e) => {
        e.currentTarget.style.outline = "none";
      }}
    >
      {/* ── Project info row ─────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "50%",
            overflow: "hidden",
            flexShrink: 0,
            backgroundColor: "var(--color-border)",
          }}
        >
          {issue.project.avatar_url ? (
            <Image
              src={issue.project.avatar_url}
              alt={`${issue.project.name} avatar`}
              width={32}
              height={32}
              style={{ display: "block" }}
            />
          ) : (
            // Fallback: first letter of project name
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700,
                fontSize: "13px",
                color: "var(--color-text-secondary)",
              }}
            >
              {issue.project.name[0]?.toUpperCase() ?? "?"}
            </div>
          )}
        </div>
        <span
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "12px",
            fontWeight: 500,
            color: "var(--color-text-secondary)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {issue.project.name}
        </span>
      </div>

      {/* ── Issue title ──────────────────────────────────────────────── */}
      <h3
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 600,
          fontSize: "0.9375rem",
          lineHeight: 1.4,
          color: "var(--color-text-primary)",
          margin: 0,
          // 2-line clamp
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {issue.title}
      </h3>

      {/* ── Tags ─────────────────────────────────────────────────────── */}
      {/* No wrapping — tags stay on one line. Max 3 shown + "+N" badge. */}
      <div style={{ display: "flex", flexWrap: "nowrap", gap: "6px", overflow: "hidden" }}>
        {visibleTags.map((type) => (
          <Tag key={type} type={type} size="sm" filterMode={false} />
        ))}
        {hiddenTagCount > 0 && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "3px 8px",
              backgroundColor: "var(--color-surface)",
              color: "var(--color-text-secondary)",
              border: "1.5px solid var(--color-border)",
              borderRadius: "999px",
              fontFamily: "'Inter', sans-serif",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            +{hiddenTagCount}
          </span>
        )}
      </div>

      {/* ── Description ──────────────────────────────────────────────── */}
      {/* flexGrow: 1 makes this section absorb all remaining vertical space
          so the card stays at its fixed height regardless of other content.
          minHeight: 0 is required for flex children to shrink below their
          natural content size in older browsers. */}
      <div
        style={{
          backgroundColor: "var(--color-bg)",
          borderRadius: "8px",
          padding: "16px",
          flexGrow: 1,
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "13px",
            lineHeight: 1.6,
            color: "var(--color-text-secondary)",
            margin: 0,
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {issue.description_display}
        </p>
      </div>

      {/* ── Bottom row: activity + AI badge ──────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: "auto",
        }}
      >
        {/* Activity dot + label */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            aria-hidden="true"
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: activityColor,
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "12px",
              color: "var(--color-text-secondary)",
            }}
          >
            {activityLabel}
          </span>
        </div>

        {/* ✨ AI-generated badge */}
        {issue.is_ai_generated && (
          <span
            aria-label="Description generated by Claude"
            title="Description generated by Claude"
            style={{ fontSize: "14px", lineHeight: 1 }}
          >
            ✨
          </span>
        )}
      </div>
    </article>
  );
}
