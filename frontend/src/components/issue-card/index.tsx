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
import { getActivityColor, formatContributionType, formatRelativeTime } from "@/lib/utils";
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
 * Clean an issue title for display on a card.
 *
 * GitHub issue titles occasionally contain backticks, leading/trailing
 * asterisks, underscores, or tildes from authors copy-pasting code or
 * markdown into the title field. Strip these so the card title renders
 * as plain readable text.
 */
function cleanTitle(text: string): string {
  return text
    // Remove all backtick characters
    .replace(/`/g, "")
    // Remove leading/trailing bold, italic, strikethrough markers
    .replace(/^[*_~]+|[*_~]+$/g, "")
    .trim();
}

/**
 * Strip markdown syntax from a description string so raw GitHub issue text
 * never shows up with headings, bold markers, blockquotes, etc. on a card.
 *
 * Rules applied (in order):
 *  1.  Drop entire lines that start with # (ATX headings)
 *  2.  Drop entire lines that are only dashes or equals (setext headings / HRs)
 *  3.  Drop entire lines that start with > (blockquotes)
 *  4.  Remove image markdown: ![alt](url) → ""
 *  5.  Unwrap links: [text](url) → text
 *  6.  Remove inline code: `code` → code
 *  7.  Remove bold (**text** / __text__) → text
 *  8.  Remove italic (*text* / _text_) → text
 *  9.  Strip leading list markers (- / * / 1.) at line start
 *  10. Collapse all newlines and runs of whitespace into a single space
 *  11. Trim and cap at 200 characters with a trailing ellipsis if needed
 */
function stripMarkdown(text: string): string {
  const cleaned = text
    // 1. Remove ATX heading lines (lines that start with one or more #)
    .replace(/^#{1,6}[^\n]*/gm, "")
    // 2. Remove setext-style heading underlines and horizontal rules
    //    (lines made entirely of dashes, equals, or asterisks)
    .replace(/^[-=*]{2,}\s*$/gm, "")
    // 3. Remove blockquote lines
    .replace(/^>+[^\n]*/gm, "")
    // 4. Remove image markdown entirely
    .replace(/!\[.*?\]\(.*?\)/g, "")
    // 5. Unwrap links — keep only the display text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    // 6. Remove inline code backticks (single or triple), keep the inner text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    // 7. Remove bold markers
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    // 8. Remove italic markers (must come after bold so ** isn't half-matched)
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/_(.*?)_/g, "$1")
    // 9. Strip list item markers at the start of a line
    .replace(/^[\s]*[-*+]\s+/gm, "")
    .replace(/^[\s]*\d+\.\s+/gm, "")
    // 10. Collapse newlines and excess whitespace into a single space
    .replace(/[\r\n]+/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();

  // 11. Cap at 200 characters so cards never show a wall of text
  return cleaned.length > 200 ? cleaned.slice(0, 197) + "…" : cleaned;
}

export function IssueCard({ issue, onClick, animationIndex }: IssueCardProps) {
  // Build a deduplicated tag list — contribution_type sometimes appears
  // again in the labels array (GitHub label matches the type name), which
  // would show the same tag twice. Set eliminates exact duplicates.
  const allTags = Array.from(new Set([issue.contribution_type, ...issue.labels]));
  // We cap tags at 3 on the card to avoid visual clutter.
  // The full tag list is shown on the detail page.
  const visibleTags = allTags.slice(0, MAX_VISIBLE_TAGS);
  const hiddenTagCount = allTags.length - visibleTags.length;

  const activityColor = getActivityColor(issue.project.activity_status);
  const activityLabel =
    ACTIVITY_LABELS[issue.project.activity_status] ?? issue.project.activity_status;

  // Strip markdown before rendering — raw syntax (###, **, -) must never show
  const cleanDescription = stripMarkdown(issue.description_display);
  const title = cleanTitle(issue.title);

  // Stagger delay: 50ms per card, capped at 300ms (index 5)
  const staggerDelay =
    animationIndex !== undefined
      ? `${Math.min(animationIndex, 5) * 50}ms`
      : undefined;

  return (
    <article
      className={animationIndex !== undefined ? "card-enter-anim" : undefined}
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
      aria-label={`${issue.title} — ${formatContributionType(issue.contribution_type)}${issue.is_bounty ? " — Bounty" : ""}`}
      style={{
        position: "relative",  // Needed for absolute-positioned bounty badge
        backgroundColor: "var(--color-surface)",
        border: `1px solid ${issue.is_bounty ? "var(--color-bounty-border)" : "var(--color-border)"}`,
        borderRadius: "12px",
        boxShadow: "var(--card-shadow)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        // Fixed height — every card is exactly this tall regardless of content.
        // overflow: hidden clips anything that would otherwise bleed out.
        // No gap here; each child section uses explicit margin/flexShrink instead
        // so the layout is fully predictable.
        height: "320px",
        overflow: "hidden",
        cursor: onClick ? "pointer" : "default",
        transition: "transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease",
        outline: "none",
        animationDelay: staggerDelay,
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
      {/* ── Bounty badge — absolute top-right corner ────────────────── */}
      {issue.is_bounty && (
        <div
          aria-label={issue.bounty_amount ? `Bounty: $${Math.floor(issue.bounty_amount / 100)}` : "Bounty"}
          style={{
            position: "absolute",
            top: "14px",
            right: "14px",
            display: "inline-flex",
            alignItems: "center",
            gap: "3px",
            padding: "3px 9px",
            backgroundColor: "var(--color-bounty-bg)",
            color: "var(--color-bounty-text)",
            border: "1.5px solid var(--color-bounty-border)",
            borderRadius: "999px",
            fontFamily: "'Inter', sans-serif",
            fontSize: "11px",
            fontWeight: 700,
            whiteSpace: "nowrap",
            zIndex: 1,
            pointerEvents: "none",  // Don't intercept card click
          }}
        >
          💰{" "}
          {issue.bounty_amount
            ? `$${Math.floor(issue.bounty_amount / 100)}`
            : "Bounty"}
        </div>
      )}

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
        {title}
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

      {/* ── Bottom row: activity status + posted time ────────────────── */}
      {/* marginTop: auto pushes this row to the bottom of the card,
          regardless of how much space the sections above occupy.
          space-between puts the activity label on the left and the
          posted time on the right — layout is identical on every card. */}
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

        {/* Posted time — right-aligned via space-between */}
        {issue.github_created_at && (
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "12px",
              color: "var(--color-text-secondary)",
            }}
          >
            {formatRelativeTime(issue.github_created_at)}
          </span>
        )}
      </div>
    </article>
  );
}
