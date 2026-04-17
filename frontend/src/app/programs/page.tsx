"use client";

/**
 * /programs — Paid stipend programs page.
 *
 * Lists curated paid programs (GSoC, Outreachy, LFX, MLH, etc.) with:
 * - Status filter tabs: All / Open / Upcoming / Closed
 * - Program cards with deadline countdown, stipend range, and CTA
 * - Loading skeletons (4 cards) while data fetches
 * - Error and empty states
 *
 * Data is fetched client-side via the usePrograms hook so the status
 * filter can change without a full page navigation.
 */

import { useState } from "react";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { ProgramCard } from "@/components/program-card";
import { usePrograms } from "@/hooks/usePrograms";
import type { Program } from "@/lib/api";

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ProgramCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "24px",
        height: "340px",
        overflow: "hidden",
      }}
    >
      {/* Org row */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
        <div className="skeleton-pulse" style={{ width: 36, height: 36, borderRadius: 8 }} />
        <div className="skeleton-pulse" style={{ width: 100, height: 12, borderRadius: 6 }} />
      </div>
      {/* Name */}
      <div className="skeleton-pulse" style={{ width: "80%", height: 16, borderRadius: 6, marginBottom: 8 }} />
      <div className="skeleton-pulse" style={{ width: "60%", height: 16, borderRadius: 6, marginBottom: 12 }} />
      {/* Stipend */}
      <div className="skeleton-pulse" style={{ width: 120, height: 14, borderRadius: 6, marginBottom: 12 }} />
      {/* Description lines */}
      <div className="skeleton-pulse" style={{ width: "100%", height: 12, borderRadius: 6, marginBottom: 6 }} />
      <div className="skeleton-pulse" style={{ width: "92%", height: 12, borderRadius: 6, marginBottom: 6 }} />
      <div className="skeleton-pulse" style={{ width: "75%", height: 12, borderRadius: 6, marginBottom: 16 }} />
      {/* Tags */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {[70, 90, 60].map((w, i) => (
          <div key={i} className="skeleton-pulse" style={{ width: w, height: 22, borderRadius: 999 }} />
        ))}
      </div>
      {/* CTA */}
      <div className="skeleton-pulse" style={{ width: "100%", height: 38, borderRadius: 8 }} />
    </div>
  );
}

// ─── Filter tabs ──────────────────────────────────────────────────────────────

type StatusFilter = "all" | "open" | "upcoming" | "closed";

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "upcoming", label: "Upcoming" },
  { value: "closed", label: "Closed" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProgramsPage() {
  const [activeStatus, setActiveStatus] = useState<StatusFilter>("all");

  // Fetch all programs; client-side filter applied for "all" so switching tabs
  // is instant without an extra network request.
  const { data, isLoading, error } = usePrograms();

  // Apply client-side status filter so tab changes are instant
  const filtered: Program[] =
    data?.data.filter((p) =>
      activeStatus === "all" ? true : p.status === activeStatus
    ) ?? [];

  // Count per status for tab badges
  const counts = {
    all: data?.data.length ?? 0,
    open: data?.data.filter((p) => p.status === "open").length ?? 0,
    upcoming: data?.data.filter((p) => p.status === "upcoming").length ?? 0,
    closed: data?.data.filter((p) => p.status === "closed").length ?? 0,
  };

  return (
    <>
      <Navbar />

      <main style={{ minHeight: "100vh", paddingTop: "60px" }}>
        {/* ── Hero ──────────────────────────────────────────────────── */}
        <section
          style={{
            background: "linear-gradient(180deg, var(--color-surface) 0%, var(--color-bg) 100%)",
            borderBottom: "1px solid var(--color-border)",
            padding: "64px 24px 48px",
          }}
        >
          <div style={{ maxWidth: "var(--content-max-width)", margin: "0 auto" }}>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "12px",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--color-cta-primary)",
                margin: "0 0 8px",
              }}
            >
              Paid Programs
            </p>
            <h1
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 800,
                fontSize: "clamp(1.75rem, 4vw, 2.5rem)",
                color: "var(--color-text-primary)",
                margin: "0 0 16px",
                lineHeight: 1.15,
              }}
            >
              Get Paid to Contribute
            </h1>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "1rem",
                lineHeight: 1.65,
                color: "var(--color-text-secondary)",
                margin: 0,
                maxWidth: "560px",
              }}
            >
              Structured stipend programmes — GSoC, Outreachy, LFX Mentorship, and more — that
              pay contributors to work on open source projects for a fixed period. Deadlines
              are shown so you never miss an application window.
            </p>
          </div>
        </section>

        {/* ── Program grid ──────────────────────────────────────────── */}
        <section
          className="page-container"
          style={{ paddingTop: "48px", paddingBottom: "100px" }}
          aria-label="Paid programs"
        >
          {/* Status filter tabs */}
          <div
            role="tablist"
            aria-label="Filter programs by status"
            style={{
              display: "flex",
              gap: "8px",
              marginBottom: "32px",
              flexWrap: "wrap",
            }}
          >
            {STATUS_TABS.map((tab) => {
              const isActive = activeStatus === tab.value;
              return (
                <button
                  key={tab.value}
                  role="tab"
                  aria-selected={isActive}
                  type="button"
                  onClick={() => setActiveStatus(tab.value)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 16px",
                    backgroundColor: isActive
                      ? "var(--color-cta-primary)"
                      : "var(--color-surface)",
                    color: isActive ? "#ffffff" : "var(--color-text-secondary)",
                    border: `1.5px solid ${isActive ? "var(--color-cta-primary)" : "var(--color-border)"}`,
                    borderRadius: "999px",
                    fontFamily: "'Inter', sans-serif",
                    fontWeight: isActive ? 600 : 500,
                    fontSize: "13px",
                    cursor: "pointer",
                    transition: "background 150ms ease, color 150ms ease",
                  }}
                >
                  {tab.label}
                  {/* Count badge */}
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minWidth: "18px",
                      height: "18px",
                      padding: "0 5px",
                      backgroundColor: isActive
                        ? "rgba(255,255,255,0.25)"
                        : "var(--color-bg)",
                      color: isActive ? "#ffffff" : "var(--color-text-secondary)",
                      borderRadius: "999px",
                      fontFamily: "'Inter', sans-serif",
                      fontSize: "10px",
                      fontWeight: 700,
                    }}
                  >
                    {counts[tab.value]}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Loading */}
          {isLoading && (
            <div
              className="issue-grid-layout"
              aria-busy="true"
              aria-label="Loading programs"
            >
              {Array.from({ length: 4 }).map((_, i) => (
                <ProgramCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Error */}
          {!isLoading && error && (
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
                We couldn&apos;t load programs right now. Try refreshing the page.
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
          )}

          {/* Empty */}
          {!isLoading && !error && filtered.length === 0 && (
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
                No {activeStatus === "all" ? "" : activeStatus} programs right now
              </p>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "0.9375rem",
                  color: "var(--color-text-secondary)",
                }}
              >
                New program cohorts are added as they are announced — check back soon.
              </p>
            </div>
          )}

          {/* Grid */}
          {!isLoading && !error && filtered.length > 0 && (
            <div className="issue-grid-layout">
              {filtered.map((program, index) => (
                <ProgramCard
                  key={program.id}
                  program={program}
                  animationIndex={index}
                />
              ))}
            </div>
          )}

          {/* Footer note */}
          {!isLoading && !error && (
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                marginTop: "40px",
                textAlign: "center",
              }}
            >
              Know a programme we&apos;re missing?{" "}
              <a
                href="mailto:hello@nocos.cc"
                style={{
                  color: "var(--color-cta-primary)",
                  textDecoration: "underline",
                }}
              >
                Let us know
              </a>
              .
            </p>
          )}
        </section>
      </main>

      <Footer />
    </>
  );
}
