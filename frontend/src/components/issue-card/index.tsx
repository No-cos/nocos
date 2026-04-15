"use client";

/**
 * IssueCard component — displays a single issue in the discovery grid.
 *
 * Layout (all sections have explicit sizes so the card is always 380px tall):
 * - Project row: avatar (32×32) + project name
 * - Title: Plus Jakarta Sans, 2-line clamp
 * - Tags: single row, no wrapping, max 3 + "+N" badge
 * - Description box: fixed 100px, 4-line clamp, markdown stripped before display
 * - Bottom row: activity dot + label (left), ✨ badge (right), pinned via marginTop: auto
 *
 * Hover: card lifts 2px, border darkens.
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

/**
 * Strip markdown syntax from a description string so raw text like
 * "### Tested versions" or "**bold**" never shows up on a card.
 *
 * Rules applied (in order):
 *  1. Remove ATX headings (# / ## / ###… lines)
 *  2. Remove bold/italic markers (** and *)
 *  3. Strip leading dashes from list items (- item → item)
 *  4. Collapse runs of whitespace / newlines into a single space
 */
function stripMarkdown(text: string): string {
  return text
    // Remove heading lines (any number of leading #s)
    .replace(/^#{1,6}\s+/gm, "")
    // Remove bold (**text** or __text__)
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    // Remove italic (*text* or _text_) — single delimiters
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/_(.*?)_/g, "$1")
    // Strip leading dash + space from list items
    .replace(/^[-*]\s+/gm, "")
    // Collapse multiple newlines / carriage returns into a space
    .replace(/[\r\n]+/g, " ")
    // Collapse multiple spaces into one
    .replace(/\s{2,}/g, " ")
    .trim();
}

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

  // Strip markdown before rendering — raw syntax (###, **, -) must never show
  const cleanDescription = stripMarkdown(issue.description_display);

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
        // Fixed height — every card is exactly this tall regardless of content.
        // overflow: hidden clips anything that would otherwise bleed out.
        // No gap here; each child section uses explicit margin/flexShrink instead
        // so the layout is fully predictable.
        height: "380px",
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
      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0, marginBottom: "12px" }}>
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
      {/* flexShrink: 0 keeps the title at its natural size (2 clamped lines).
          Without this the title can be squeezed by siblings in the flex column. */}
      <h3
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 600,
          fontSize: "0.9375rem",
          lineHeight: 1.4,
          color: "var(--color-text-primary)",
          margin: 0,
          marginBottom: "10px",
          flexShrink: 0,
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
      {/* No wrapping — tags stay on one line. flexShrink: 0 keeps single row. */}
      <div style={{ display: "flex", flexWrap: "nowrap", gap: "6px", overflow: "hidden", flexShrink: 0, marginBottom: "12px" }}>
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
      {/* Fixed height of 100px + flexShrink: 0 means this box never grows
          or shrinks regardless of text length. overflow: hidden clips excess.
          Text is also clamped to 4 lines as a belt-and-braces measure. */}
      <div
        style={{
          backgroundColor: "var(--color-bg)",
          borderRadius: "8px",
          padding: "12px 14px",
          height: "100px",
          flexShrink: 0,
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
            WebkitLineClamp: 4,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {cleanDescription}
        </p>
      </div>

      {/* ── Bottom row: activity + AI badge ──────────────────────────── */}
      {/* marginTop: auto pushes this row to the bottom of the 380px card,
          regardless of how much space the sections above occupy. */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: "auto",
          flexShrink: 0,
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
