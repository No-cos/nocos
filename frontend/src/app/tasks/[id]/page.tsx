"use client";

/**
 * Task Detail Page — /tasks/[id]
 *
 * Single-column layout centred at max-width 720px.
 * Fetches issue + embedded project from GET /api/v1/issues/:id.
 *
 * Sections (in order):
 *   1. Issue section: title, tags, description, AI notice, GitHub link, bookmark
 *   2. About This Project: avatar, name, description, website, social links, activity
 *   3. Related Issues: horizontal scroll carousel of other tasks from same project
 *   4. Primary CTA: "View Issue on GitHub →" full-width button
 *
 * description_original is never rendered — only description_display (SKILLS.md §16).
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { Tag } from "@/components/ui/tag";
import { ProjectAbout } from "@/components/project-about";
import { RelatedIssues } from "@/components/related-issues";
import { useIssue } from "@/hooks/useIssue";
import { useBookmark } from "@/hooks/useBookmark";
import { DetailPageSkeleton } from "./skeleton";

export default function TaskDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";

  const { data: issue, isLoading, error, notFound } = useIssue(id);
  const { isBookmarked, toggle: toggleBookmark } = useBookmark(id);

  // Defer all rendering to the client to prevent server/client HTML mismatch.
  // This component relies on client-only hooks (useParams, useIssue, useBookmark)
  // that produce different output on the server.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  if (!mounted) return null;

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <>
        <PageShell>
          <DetailPageSkeleton />
        </PageShell>
      </>
    );
  }

  // ── Not found ─────────────────────────────────────────────────────────────
  if (notFound) {
    return (
      <PageShell>
        <div
          style={{ textAlign: "center", padding: "80px 24px" }}
          role="alert"
        >
          <p
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "1.25rem",
              color: "var(--color-text-primary)",
              marginBottom: "12px",
            }}
          >
            Task not found
          </p>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--color-text-secondary)",
              marginBottom: "28px",
            }}
          >
            This task may have been closed or removed.
          </p>
          <Link
            href="/"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              fontSize: "0.9375rem",
              color: "var(--color-cta-primary)",
              textDecoration: "underline",
            }}
          >
            Browse all tasks →
          </Link>
        </div>
      </PageShell>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error || !issue) {
    return (
      <PageShell>
        <div
          style={{ textAlign: "center", padding: "80px 24px" }}
          role="alert"
        >
          <p
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "1.25rem",
              color: "var(--color-text-primary)",
              marginBottom: "12px",
            }}
          >
            Something went wrong
          </p>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--color-text-secondary)",
              marginBottom: "28px",
            }}
          >
            {error ?? "Could not load this task."}
          </p>
          <Link
            href="/"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              fontSize: "0.9375rem",
              color: "var(--color-cta-primary)",
              textDecoration: "underline",
            }}
          >
            Browse all tasks →
          </Link>
        </div>
      </PageShell>
    );
  }

  // ── Data ───────────────────────────────────────────────────────────────────
  const allTags = [issue.contribution_type, ...issue.labels].filter(Boolean);

  return (
    <>
      <Navbar />
      <PageShell>
        {/* Extra bottom padding leaves room for the fixed CTA button */}
        <div
          style={{
            maxWidth: "720px",
            margin: "0 auto",
            padding: "40px 24px 100px",
          }}
        >
          {/* ── Issue Section ────────────────────────────────────────────── */}
          <section aria-labelledby="issue-title">
            {/* Title row with bookmark icon */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
                marginBottom: "20px",
              }}
            >
              <h1
                id="issue-title"
                style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 700,
                  fontSize: "clamp(1.375rem, 3vw, 1.75rem)",
                  lineHeight: 1.3,
                  color: "var(--color-text-primary)",
                  margin: 0,
                }}
              >
                {issue.title}
              </h1>

              {/* Bookmark toggle */}
              <button
                onClick={toggleBookmark}
                aria-label={
                  isBookmarked ? "Remove bookmark" : "Bookmark this task"
                }
                aria-pressed={isBookmarked}
                style={{
                  flexShrink: 0,
                  background: "none",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  padding: "8px 10px",
                  cursor: "pointer",
                  fontSize: "18px",
                  lineHeight: 1,
                  color: isBookmarked
                    ? "var(--color-cta-primary)"
                    : "var(--color-text-secondary)",
                  transition: "color 150ms ease, border-color 150ms ease",
                }}
              >
                {isBookmarked ? "🔖" : "🔖"}
                <span
                  className="sr-only"
                >
                  {isBookmarked ? "Bookmarked" : "Bookmark"}
                </span>
              </button>
            </div>

            {/* Tags */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                marginBottom: "24px",
              }}
            >
              {allTags.map((type) => (
                <Tag key={type} type={type} size="md" />
              ))}
              {issue.is_paid && <Tag type="paid" size="md" />}
              {issue.difficulty === "beginner" && (
                <Tag type="beginner" size="md" />
              )}
            </div>

            {/* Description — only description_display is ever shown here */}
            <div
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "1rem",
                lineHeight: 1.75,
                color: "var(--color-text-primary)",
                marginBottom: issue.is_ai_generated ? "12px" : "20px",
              }}
            >
              {issue.description_display}
            </div>

            {/* AI-generated notice */}
            {issue.is_ai_generated && (
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "12px",
                  color: "var(--color-text-secondary)",
                  margin: "0 0 20px",
                }}
              >
                ✨ This description was generated by Claude
              </p>
            )}

            {/* GitHub issue URL */}
            <a
              href={issue.github_issue_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontFamily: "'Inter', sans-serif",
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                textDecoration: "none",
                transition: "color 150ms ease",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLElement).style.color =
                  "var(--color-text-primary)")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLElement).style.color =
                  "var(--color-text-secondary)")
              }
            >
              {/* Link icon */}
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
              {issue.github_issue_url}
            </a>
          </section>

          {/* ── Divider ──────────────────────────────────────────────────── */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--color-border)",
              margin: "36px 0",
            }}
          />

          {/* ── About This Project ───────────────────────────────────────── */}
          <ProjectAbout project={issue.project} />

          {/* ── Divider ──────────────────────────────────────────────────── */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--color-border)",
              margin: "36px 0",
            }}
          />

          {/* ── Related Issues ───────────────────────────────────────────── */}
          <RelatedIssues
            projectId={issue.project_id}
            currentIssueId={issue.id}
            projectName={issue.project.name}
          />
        </div>
      </PageShell>

      {/* ── Primary CTA — fixed to bottom on mobile, static on desktop ─── */}
      <div className="cta-wrapper">
        <a
          href={issue.github_issue_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "block",
            width: "100%",
            maxWidth: "720px",
            margin: "0 auto",
            padding: "16px",
            backgroundColor: "var(--color-cta-primary)",
            color: "#ffffff",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "1rem",
            textAlign: "center",
            textDecoration: "none",
            borderRadius: "12px",
            transition: "opacity 150ms ease",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "0.88")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "1")
          }
        >
          View Issue on GitHub →
        </a>
      </div>

    </>
  );
}

// ── Shared page shell ─────────────────────────────────────────────────────────

/**
 * PageShell — wraps detail page content with the background colour and
 * a min-height so the page never looks empty during loading.
 */
function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--color-bg)",
        paddingTop: "80px",
      }}
    >
      {children}
    </div>
  );
}
