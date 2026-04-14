"use client";

/**
 * IssueGrid component — the main issue discovery grid on the landing page.
 *
 * Fetches issues from GET /api/v1/issues using the useIssues hook, wiring
 * the filter bar and search bar state into the query parameters.
 *
 * States handled (SKILLS.md §6):
 * - Loading: 12 skeleton cards (not a spinner)
 * - Error:   friendly message with retry button
 * - Empty:   friendly message (adjust filters suggestion)
 * - Data:    3-col desktop / 2-col tablet / 1-col mobile grid + pagination
 *
 * @param activeTypes - Selected contribution type filters from FilterBar
 * @param search      - Search string from SearchBar
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useIssues } from "@/hooks/useIssues";
import { IssueCard } from "@/components/issue-card";
import { IssueCardSkeleton } from "./skeleton";
import { Pagination } from "./pagination";

const PAGE_SIZE = 12;

interface IssueGridProps {
  activeTypes: string[];
  search: string;
}

export function IssueGrid({ activeTypes, search }: IssueGridProps) {
  const router = useRouter();
  const [page, setPage] = useState(1);

  // Reset to page 1 whenever filters or search changes to avoid empty pages
  const effectivePage = page;

  const { data, isLoading, error } = useIssues({
    page: effectivePage,
    limit: PAGE_SIZE,
    types: activeTypes.length > 0 ? activeTypes.join(",") : undefined,
    search: search || undefined,
  });

  const totalPages = data ? Math.ceil(data.meta.total / PAGE_SIZE) : 0;

  function handlePageChange(newPage: number) {
    setPage(newPage);
    // Scroll to top of grid on page change so the user sees the new items
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div>
        <div className="issue-grid-layout" aria-busy="true" aria-label="Loading issues">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <IssueCardSkeleton key={i} />
          ))}
        </div>
        <GridStyles />
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "60px 24px" }} role="alert">
        <p
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "1.125rem",
            color: "var(--color-text-primary)",
            marginBottom: "8px",
          }}
        >
          Something went wrong
        </p>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "0.9375rem",
            color: "var(--color-text-secondary)",
            marginBottom: "24px",
          }}
        >
          We couldn't load issues right now. Try refreshing the page.
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: "10px 24px",
            backgroundColor: "var(--color-cta-primary)",
            color: "#ffffff",
            border: "none",
            borderRadius: "8px",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "0.9375rem",
            cursor: "pointer",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // ── Empty ─────────────────────────────────────────────────────────────────
  if (!data || data.data.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "60px 24px" }}>
        <p
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "1.125rem",
            color: "var(--color-text-primary)",
            marginBottom: "8px",
          }}
        >
          No issues found
        </p>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "0.9375rem",
            color: "var(--color-text-secondary)",
          }}
        >
          Try adjusting your filters or check back soon — new issues are added
          every 6 hours.
        </p>
      </div>
    );
  }

  // ── Data ──────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
      <div className="issue-grid-layout">
        {data.data.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onClick={() => router.push(`/tasks/${issue.id}`)}
          />
        ))}
      </div>

      <Pagination
        currentPage={effectivePage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />

      <GridStyles />
    </div>
  );
}

// CSS grid layout — 3 columns desktop, 2 tablet, 1 mobile (SKILLS.md §11)
function GridStyles() {
  return (
    <style>{`
      .issue-grid-layout {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
      }
      @media (max-width: 1024px) {
        .issue-grid-layout {
          grid-template-columns: repeat(2, 1fr);
        }
      }
      @media (max-width: 639px) {
        .issue-grid-layout {
          grid-template-columns: 1fr;
        }
      }
    `}</style>
  );
}
