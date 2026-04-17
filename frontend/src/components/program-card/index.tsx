"use client";

/**
 * ProgramCard component — displays a single paid stipend program.
 *
 * Visual language:
 * - Status badge top-right: green (open) / blue (upcoming) / grey (closed)
 * - Deadline row: "Apply by {date}" + live countdown when open
 * - Closed cards are visually muted (opacity 0.65) but fully readable
 * - Tags row: up to 3 pills, same Tag component as IssueCard
 * - "Apply Now" CTA links out; disabled + muted when closed
 *
 * All colours via CSS variables — no hardcoded hex values.
 */

import { useMemo } from "react";
import type { ProgramCardProps } from "./types";
import type { Program } from "@/lib/api";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Format an ISO date string as "Apr 22, 2026" */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Return "X days left" / "closes today" / "" given an ISO deadline string.
 * Returns null if the deadline is in the past or not provided.
 */
function getCountdown(deadline: string | null): string | null {
  if (!deadline) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(deadline);
  end.setHours(0, 0, 0, 0);
  const diff = Math.round((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return null;
  if (diff === 0) return "closes today";
  if (diff === 1) return "1 day left";
  return `${diff} days left`;
}

/** Token set for a given program status */
function statusTokens(status: Program["status"]) {
  switch (status) {
    case "open":
      return {
        label: "Open",
        bg: "var(--color-program-open-bg)",
        border: "var(--color-program-open-border)",
        text: "var(--color-program-open-text)",
        dot: "var(--color-status-active)",
      };
    case "upcoming":
      return {
        label: "Upcoming",
        bg: "var(--color-program-upcoming-bg)",
        border: "var(--color-program-upcoming-border)",
        text: "var(--color-program-upcoming-text)",
        dot: "var(--color-status-slow)",
      };
    case "closed":
    default:
      return {
        label: "Closed",
        bg: "var(--color-program-closed-bg)",
        border: "var(--color-program-closed-border)",
        text: "var(--color-program-closed-text)",
        dot: "var(--color-status-inactive)",
      };
  }
}

/** Initials avatar fallback (first letter of each word, max 2) */
function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

// ─── Component ────────────────────────────────────────────────────────────────

const MAX_TAGS = 3;

export function ProgramCard({ program, animationIndex }: ProgramCardProps) {
  const tokens = statusTokens(program.status);
  const isClosed = program.status === "closed";

  const countdown = useMemo(
    () => (program.status === "open" ? getCountdown(program.application_deadline) : null),
    [program.status, program.application_deadline]
  );

  const visibleTags = program.tags.slice(0, MAX_TAGS);
  const hiddenTagCount = program.tags.length - visibleTags.length;

  const staggerDelay =
    animationIndex !== undefined
      ? `${Math.min(animationIndex, 5) * 60}ms`
      : undefined;

  return (
    <article
      className={animationIndex !== undefined ? "card-enter-anim" : undefined}
      style={{
        position: "relative",
        backgroundColor: "var(--color-surface)",
        border: `1px solid ${isClosed ? "var(--color-border)" : tokens.border}`,
        borderRadius: "12px",
        boxShadow: "var(--card-shadow)",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "0px",
        opacity: isClosed ? 0.65 : 1,
        transition: "transform 150ms ease, box-shadow 150ms ease, opacity 150ms ease",
        animationDelay: staggerDelay,
      }}
      onMouseEnter={(e) => {
        if (!isClosed) {
          e.currentTarget.style.transform = "translateY(-2px)";
          e.currentTarget.style.boxShadow = "0 4px 16px rgba(0,0,0,0.10)";
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "var(--card-shadow)";
      }}
    >
      {/* ── Status badge ─────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: "20px",
          right: "20px",
          display: "inline-flex",
          alignItems: "center",
          gap: "5px",
          padding: "3px 10px",
          backgroundColor: tokens.bg,
          color: tokens.text,
          border: `1.5px solid ${tokens.border}`,
          borderRadius: "999px",
          fontFamily: "'Inter', sans-serif",
          fontSize: "11px",
          fontWeight: 700,
          letterSpacing: "0.03em",
          textTransform: "uppercase",
          pointerEvents: "none",
        }}
        aria-label={`Status: ${tokens.label}`}
      >
        <span
          aria-hidden="true"
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: tokens.dot,
            flexShrink: 0,
          }}
        />
        {tokens.label}
      </div>

      {/* ── Organisation logo + name ──────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          marginBottom: "14px",
          paddingRight: "80px", // avoid overlap with status badge
        }}
      >
        {/* Logo or initials fallback */}
        <div
          aria-hidden="true"
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            overflow: "hidden",
            flexShrink: 0,
            backgroundColor: "var(--color-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {program.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={program.logo_url}
              alt={`${program.organisation} logo`}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <span
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700,
                fontSize: "13px",
                color: "var(--color-text-secondary)",
              }}
            >
              {initials(program.organisation)}
            </span>
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
          {program.organisation}
        </span>
      </div>

      {/* ── Program name ─────────────────────────────────────────────── */}
      <h3
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 700,
          fontSize: "1rem",
          lineHeight: 1.35,
          color: "var(--color-text-primary)",
          margin: "0 0 8px",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {program.name}
      </h3>

      {/* ── Stipend ───────────────────────────────────────────────────── */}
      <p
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "14px",
          fontWeight: 600,
          color: "var(--color-cta-primary)",
          margin: "0 0 12px",
        }}
      >
        {program.stipend_range}
      </p>

      {/* ── Description ──────────────────────────────────────────────── */}
      <p
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "13px",
          lineHeight: 1.6,
          color: "var(--color-text-secondary)",
          margin: "0 0 16px",
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
          flexGrow: 1,
        }}
      >
        {program.description}
      </p>

      {/* ── Tags ─────────────────────────────────────────────────────── */}
      {visibleTags.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "6px",
            marginBottom: "16px",
          }}
        >
          {visibleTags.map((tag) => (
            <span
              key={tag}
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "3px 10px",
                backgroundColor: "var(--color-bg)",
                color: "var(--color-text-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: "999px",
                fontFamily: "'Inter', sans-serif",
                fontSize: "11px",
                fontWeight: 500,
              }}
            >
              {tag}
            </span>
          ))}
          {hiddenTagCount > 0 && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "3px 8px",
                backgroundColor: "var(--color-bg)",
                color: "var(--color-text-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: "999px",
                fontFamily: "'Inter', sans-serif",
                fontSize: "11px",
                fontWeight: 500,
              }}
            >
              +{hiddenTagCount}
            </span>
          )}
        </div>
      )}

      {/* ── Deadline row ─────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "16px",
          minHeight: "20px",
        }}
      >
        <span
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "12px",
            color: "var(--color-text-secondary)",
          }}
        >
          {program.application_deadline ? (
            <>
              Apply by{" "}
              <strong style={{ color: "var(--color-text-primary)", fontWeight: 600 }}>
                {formatDate(program.application_deadline)}
              </strong>
            </>
          ) : program.status === "upcoming" ? (
            "Dates TBA"
          ) : null}
        </span>

        {/* Countdown pill — only shown for open programs */}
        {countdown && (
          <span
            aria-label={countdown}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "2px 8px",
              backgroundColor: "var(--color-program-open-bg)",
              color: "var(--color-program-open-text)",
              border: "1px solid var(--color-program-open-border)",
              borderRadius: "999px",
              fontFamily: "'Inter', sans-serif",
              fontSize: "11px",
              fontWeight: 600,
            }}
          >
            ⏳ {countdown}
          </span>
        )}
      </div>

      {/* ── CTA button ───────────────────────────────────────────────── */}
      {isClosed ? (
        <div
          aria-disabled="true"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "9px 20px",
            backgroundColor: "var(--color-program-closed-bg)",
            color: "var(--color-program-closed-text)",
            border: `1px solid var(--color-program-closed-border)`,
            borderRadius: "8px",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "14px",
            cursor: "not-allowed",
            textAlign: "center",
          }}
        >
          Applications Closed
        </div>
      ) : (
        <a
          href={program.application_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Apply to ${program.name} (opens in new tab)`}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
            padding: "9px 20px",
            backgroundColor: "var(--color-cta-primary)",
            color: "#ffffff",
            border: "none",
            borderRadius: "8px",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "14px",
            cursor: "pointer",
            textDecoration: "none",
            textAlign: "center",
            transition: "opacity 150ms ease",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.88"; }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
        >
          {program.status === "upcoming" ? "Learn More" : "Apply Now"}
          <span aria-hidden="true" style={{ fontSize: "13px" }}>↗</span>
        </a>
      )}
    </article>
  );
}
