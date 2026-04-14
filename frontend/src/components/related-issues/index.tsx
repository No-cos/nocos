"use client";

/**
 * RelatedIssues component — horizontal scrollable carousel of other issues
 * from the same project on the task detail page.
 *
 * Behaviour:
 * - Fetches up to 6 issues from the same project, excluding the current issue.
 * - Renders nothing if there are no related issues (hides the section entirely).
 * - Left/right arrow buttons scroll the carousel by one card width (~240px).
 * - Each card navigates to /tasks/[id] on click.
 * - Uses the existing IssueCard component in its standard form.
 *
 * Data fetching:
 * - Calls GET /api/v1/issues?project_id=... directly via fetchIssues.
 *   The API doesn't expose a project_id filter yet, so we pass the type
 *   filter as empty and filter by project client-side from the first page.
 *   (When the API adds project_id support this can be simplified.)
 *
 * All colours via CSS variables — no hardcoded hex values.
 *
 * @param projectId      - UUID of the project whose issues to show
 * @param currentIssueId - UUID of the issue currently being viewed (excluded)
 * @param projectName    - Display name of the project (used in section label)
 */

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchIssues } from "@/lib/api";
import { IssueCard } from "@/components/issue-card";
import { getMockIssues } from "@/lib/mock-data";
import type { Issue } from "@/lib/api";

const IS_DEV = process.env.NODE_ENV === "development";

interface RelatedIssuesProps {
  projectId: string;
  currentIssueId: string;
  projectName: string;
}

// How many related issues to show at most
const MAX_RELATED = 6;

// Scroll distance per arrow click (roughly one card + gap)
const SCROLL_STEP = 260;

export function RelatedIssues({
  projectId,
  currentIssueId,
  projectName,
}: RelatedIssuesProps) {
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);

  const [issues, setIssues] = useState<Issue[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        // Fetch a broad first page and filter client-side by project.
        // We over-fetch (limit 50) so we have enough candidates after
        // excluding the current issue and capping at MAX_RELATED.
        const result = await fetchIssues({ limit: 50, page: 1 });
        if (cancelled) return;

        const related = result.data
          .filter(
            (issue) =>
              issue.project_id === projectId && issue.id !== currentIssueId
          )
          .slice(0, MAX_RELATED);

        setIssues(related);
      } catch {
        if (cancelled) return;
        if (IS_DEV) {
          // Backend not running — fall back to mock data
          const mockResult = getMockIssues({ limit: 50 });
          const related = mockResult.data
            .filter(
              (issue) =>
                issue.project_id === projectId && issue.id !== currentIssueId
            )
            .slice(0, MAX_RELATED);
          if (!cancelled) setIssues(related);
        } else {
          if (!cancelled) setIssues([]);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [projectId, currentIssueId]);

  // Hide section entirely while loading or when there are no related issues
  if (isLoading || issues.length === 0) return null;

  function scrollLeft() {
    scrollRef.current?.scrollBy({ left: -SCROLL_STEP, behavior: "smooth" });
  }

  function scrollRight() {
    scrollRef.current?.scrollBy({ left: SCROLL_STEP, behavior: "smooth" });
  }

  return (
    <section aria-labelledby="related-issues-label">
      {/* Header row: section label + arrow buttons */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "16px",
        }}
      >
        <p
          id="related-issues-label"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "11px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--color-text-secondary)",
            margin: 0,
          }}
        >
          More from {projectName}
        </p>

        {/* Arrow navigation */}
        <div style={{ display: "flex", gap: "8px" }}>
          <ArrowButton direction="left" onClick={scrollLeft} />
          <ArrowButton direction="right" onClick={scrollRight} />
        </div>
      </div>

      {/* Horizontal scroll container */}
      <div
        ref={scrollRef}
        role="list"
        style={{
          display: "flex",
          gap: "16px",
          overflowX: "auto",
          // Hide scrollbar visually while keeping scroll functional
          scrollbarWidth: "none",
          msOverflowStyle: "none",
          paddingBottom: "4px",
          // Snap to card edges for a polished feel on touch/trackpad
          scrollSnapType: "x mandatory",
        }}
      >
        {issues.map((issue) => (
          <div
            key={issue.id}
            role="listitem"
            style={{
              flexShrink: 0,
              width: "240px",
              scrollSnapAlign: "start",
            }}
          >
            <IssueCard
              issue={issue}
              onClick={() => router.push(`/tasks/${issue.id}`)}
            />
          </div>
        ))}
      </div>

    </section>
  );
}

// ── Arrow button sub-component ────────────────────────────────────────────────

interface ArrowButtonProps {
  direction: "left" | "right";
  onClick: () => void;
}

function ArrowButton({ direction, onClick }: ArrowButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={direction === "left" ? "Scroll left" : "Scroll right"}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: "32px",
        height: "32px",
        borderRadius: "8px",
        border: "1px solid var(--color-border)",
        backgroundColor: "transparent",
        color: "var(--color-text-secondary)",
        cursor: "pointer",
        transition: "color 150ms ease, border-color 150ms ease",
        padding: 0,
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.color = "var(--color-text-primary)";
        el.style.borderColor = "var(--color-text-secondary)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.color = "var(--color-text-secondary)";
        el.style.borderColor = "var(--color-border)";
      }}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {direction === "left" ? (
          <polyline points="15 18 9 12 15 6" />
        ) : (
          <polyline points="9 18 15 12 9 6" />
        )}
      </svg>
    </button>
  );
}
