"use client";

/**
 * AITaskBanner — dev-only UI for the AI Task Generator feature.
 *
 * Three states:
 *   input     → user pastes a GitHub URL and clicks Generate
 *   preview   → Claude's generated tasks are shown for review
 *   published → confirmation after the user clicks Publish
 *
 * The entire component returns null in production (NODE_ENV !== "development")
 * so it can safely be placed in the page layout without any conditional
 * rendering at the call site.
 *
 * API surface:
 *   POST /api/v1/generate-tasks/preview  — generates, does NOT save to DB
 *   POST /api/v1/generate-tasks/publish  — saves the reviewed tasks to DB
 */

import { useState, useRef } from "react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface GeneratedTask {
  title: string;
  description: string;
  category: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  estimated_hours: 3 | 6 | 10;
}

type BannerState = "input" | "preview" | "published";

// ── Shared style tokens ────────────────────────────────────────────────────────

const FONT_SANS = "'Inter', sans-serif";
const FONT_HEADING = "'Plus Jakarta Sans', sans-serif";

// ── Category badge colours (reuse existing CSS variables) ──────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  documentation: "var(--color-type-documentation, #4B7BE5)",
  design:        "var(--color-type-design, #C850C0)",
  translation:   "var(--color-type-translation, #2EB87E)",
  community:     "var(--color-type-community, #F5A623)",
  marketing:     "var(--color-type-marketing, #E5534B)",
  research:      "var(--color-type-research, #8B6FD4)",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  beginner:     "Beginner",
  intermediate: "Intermediate",
  advanced:     "Advanced",
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function isGitHubRepoUrl(url: string): boolean {
  return /^https:\/\/github\.com\/[^/]+\/[^/]+\/?$/.test(url.trim());
}

function repoNameFromUrl(url: string): string {
  const parts = url.trim().replace(/\/$/, "").split("/");
  return parts.slice(-2).join("/");
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-block",
        width: "14px",
        height: "14px",
        border: "2px solid rgba(255,255,255,0.35)",
        borderTopColor: "#fff",
        borderRadius: "50%",
        animation: "ai-spin 0.7s linear infinite",
        flexShrink: 0,
      }}
    />
  );
}

function CategoryBadge({ category }: { category: string }) {
  const color = CATEGORY_COLORS[category] ?? "var(--color-text-secondary)";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "999px",
        fontFamily: FONT_SANS,
        fontSize: "11px",
        fontWeight: 600,
        color,
        border: `1.5px solid ${color}`,
        backgroundColor: "transparent",
        whiteSpace: "nowrap",
        textTransform: "capitalize",
      }}
    >
      {category}
    </span>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "999px",
        fontFamily: FONT_SANS,
        fontSize: "11px",
        fontWeight: 500,
        color: "var(--color-text-secondary)",
        border: "1.5px solid var(--color-border)",
        whiteSpace: "nowrap",
      }}
    >
      {DIFFICULTY_LABELS[difficulty] ?? difficulty}
    </span>
  );
}

function TaskPreviewItem({ task, index }: { task: GeneratedTask; index: number }) {
  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: "10px",
        backgroundColor: "var(--color-bg)",
        border: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
      }}
    >
      {/* Title row */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <p
          style={{
            fontFamily: FONT_HEADING,
            fontWeight: 700,
            fontSize: "14px",
            color: "var(--color-text-primary)",
            margin: 0,
            flex: 1,
            minWidth: 0,
          }}
        >
          {task.title}
        </p>
        <div style={{ display: "flex", gap: "6px", flexShrink: 0, flexWrap: "wrap" }}>
          <CategoryBadge category={task.category} />
          <DifficultyBadge difficulty={task.difficulty} />
        </div>
      </div>

      {/* Description */}
      <p
        style={{
          fontFamily: FONT_SANS,
          fontSize: "13px",
          color: "var(--color-text-secondary)",
          margin: 0,
          lineHeight: 1.55,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {task.description}
      </p>

      {/* Hours hint */}
      <p
        style={{
          fontFamily: FONT_SANS,
          fontSize: "11px",
          color: "var(--color-text-secondary)",
          margin: 0,
          opacity: 0.7,
        }}
      >
        ≈ {task.estimated_hours} hrs
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function AITaskBanner() {
  // Never render in production
  if (process.env.NODE_ENV !== "development") return null;

  const [state, setState] = useState<BannerState>("input");
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState("");
  const [tasks, setTasks] = useState<GeneratedTask[]>([]);
  const [repoName, setRepoName] = useState("");
  const [publishedCount, setPublishedCount] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const API_BASE =
    typeof process !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
      : "http://localhost:8000";

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setUrlError("");
    setApiError("");

    const trimmed = url.trim();
    if (!trimmed) {
      setUrlError("Please enter a GitHub URL.");
      return;
    }
    if (!isGitHubRepoUrl(trimmed)) {
      setUrlError("Enter a valid GitHub repo URL, e.g. https://github.com/owner/repo");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/generate-tasks/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: trimmed }),
      });

      const json = await res.json();

      if (!res.ok) {
        setApiError(
          json?.detail?.error ??
          json?.detail ??
          "Something went wrong. Please try again."
        );
        return;
      }

      setTasks(json.data.tasks ?? []);
      setRepoName(json.data.repo_name ?? repoNameFromUrl(trimmed));
      setState("preview");
    } catch {
      setApiError("Could not reach the server. Make sure the backend is running.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handlePublish() {
    setApiError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/generate-tasks/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url.trim(), tasks }),
      });

      const json = await res.json();

      if (!res.ok) {
        setApiError(
          json?.detail?.error ??
          json?.detail ??
          "Publish failed. Please try again."
        );
        return;
      }

      setPublishedCount(json.data.saved_count ?? tasks.length);
      setState("published");
    } catch {
      setApiError("Could not reach the server. Make sure the backend is running.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleClear() {
    // Discard preview — nothing was saved
    setTasks([]);
    setRepoName("");
    setApiError("");
    setState("input");
  }

  function handleReset() {
    setUrl("");
    setUrlError("");
    setApiError("");
    setTasks([]);
    setRepoName("");
    setPublishedCount(0);
    setState("input");
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  // ── Layout wrapper shared across all states ────────────────────────────────

  return (
    <>
      {/* Keyframe for spinner — injected once, no external dep needed */}
      <style>{`
        @keyframes ai-spin { to { transform: rotate(360deg); } }
      `}</style>

      <div
        aria-label="AI task generator (development only)"
        style={{
          borderRadius: "16px",
          border: "1.5px solid var(--color-cta-primary)",
          backgroundColor: "var(--color-surface)",
          padding: "28px 28px 24px",
          marginBottom: "32px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Dev-only watermark strip */}
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "3px",
            background:
              "linear-gradient(90deg, var(--color-cta-primary), #a855f7, var(--color-cta-primary))",
          }}
        />

        {/* ── STATE 1: Input ────────────────────────────────────────── */}
        {state === "input" && (
          <form onSubmit={handleGenerate} noValidate>
            {/* Dev badge */}
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "2px 8px",
                borderRadius: "999px",
                fontFamily: FONT_SANS,
                fontSize: "10px",
                fontWeight: 700,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                color: "var(--color-cta-primary)",
                border: "1.5px solid var(--color-cta-primary)",
                marginBottom: "14px",
              }}
            >
              Dev only
            </span>

            <h3
              style={{
                fontFamily: FONT_HEADING,
                fontWeight: 800,
                fontSize: "1.125rem",
                color: "var(--color-text-primary)",
                margin: "0 0 6px",
                lineHeight: 1.3,
              }}
            >
              ✦ Generate tasks for any open source repo
            </h3>

            <p
              style={{
                fontFamily: FONT_SANS,
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                margin: "0 0 20px",
                lineHeight: 1.55,
              }}
            >
              Paste a GitHub URL — Claude will find non-code contribution
              opportunities automatically
            </p>

            {/* Input + button row */}
            <div
              style={{
                display: "flex",
                gap: "10px",
                flexWrap: "wrap",
                alignItems: "flex-start",
              }}
            >
              <div style={{ flex: 1, minWidth: "220px" }}>
                <input
                  ref={inputRef}
                  type="url"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (urlError) setUrlError("");
                  }}
                  placeholder="https://github.com/owner/repo"
                  disabled={isLoading}
                  aria-label="GitHub repository URL"
                  aria-invalid={!!urlError}
                  aria-describedby={urlError ? "url-error" : undefined}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "10px 14px",
                    fontFamily: FONT_SANS,
                    fontSize: "14px",
                    color: "var(--color-text-primary)",
                    backgroundColor: "var(--color-bg)",
                    border: `1.5px solid ${urlError ? "#E5534B" : "var(--color-border)"}`,
                    borderRadius: "8px",
                    outline: "none",
                    transition: "border-color 150ms ease",
                    opacity: isLoading ? 0.6 : 1,
                  }}
                  onFocus={(e) => {
                    if (!urlError) e.currentTarget.style.borderColor = "var(--color-cta-primary)";
                  }}
                  onBlur={(e) => {
                    if (!urlError) e.currentTarget.style.borderColor = "var(--color-border)";
                  }}
                />
                {urlError && (
                  <p
                    id="url-error"
                    role="alert"
                    style={{
                      fontFamily: FONT_SANS,
                      fontSize: "12px",
                      color: "#E5534B",
                      margin: "5px 0 0",
                    }}
                  >
                    {urlError}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 20px",
                  backgroundColor: "var(--color-cta-primary)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "8px",
                  fontFamily: FONT_SANS,
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: isLoading ? "not-allowed" : "pointer",
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                  opacity: isLoading ? 0.75 : 1,
                  transition: "opacity 150ms ease",
                }}
              >
                {isLoading ? (
                  <>
                    <Spinner />
                    Analysing repo…
                  </>
                ) : (
                  "Generate →"
                )}
              </button>
            </div>

            {apiError && (
              <p
                role="alert"
                style={{
                  fontFamily: FONT_SANS,
                  fontSize: "13px",
                  color: "#E5534B",
                  margin: "12px 0 0",
                }}
              >
                {apiError}
              </p>
            )}
          </form>
        )}

        {/* ── STATE 2: Preview ──────────────────────────────────────── */}
        {state === "preview" && (
          <div>
            <p
              style={{
                fontFamily: FONT_SANS,
                fontSize: "11px",
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--color-cta-primary)",
                margin: "0 0 6px",
              }}
            >
              ✦ Preview — review before publishing
            </p>

            <h3
              style={{
                fontFamily: FONT_HEADING,
                fontWeight: 800,
                fontSize: "1.0625rem",
                color: "var(--color-text-primary)",
                margin: "0 0 18px",
              }}
            >
              {tasks.length} tasks generated for{" "}
              <span style={{ color: "var(--color-cta-primary)" }}>{repoName}</span>
            </h3>

            {/* Task list */}
            <div
              style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}
            >
              {tasks.map((task, i) => (
                <TaskPreviewItem key={i} task={task} index={i} />
              ))}
            </div>

            {/* Action buttons */}
            <div
              style={{
                display: "flex",
                gap: "10px",
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <button
                type="button"
                onClick={handlePublish}
                disabled={isLoading}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 20px",
                  backgroundColor: "var(--color-cta-primary)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "8px",
                  fontFamily: FONT_SANS,
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: isLoading ? "not-allowed" : "pointer",
                  opacity: isLoading ? 0.75 : 1,
                  transition: "opacity 150ms ease",
                }}
              >
                {isLoading ? (
                  <>
                    <Spinner />
                    Publishing…
                  </>
                ) : (
                  `Publish ${tasks.length} tasks`
                )}
              </button>

              <button
                type="button"
                onClick={handleClear}
                disabled={isLoading}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "10px 20px",
                  backgroundColor: "transparent",
                  color: "var(--color-text-secondary)",
                  border: "1.5px solid var(--color-border)",
                  borderRadius: "8px",
                  fontFamily: FONT_SANS,
                  fontWeight: 500,
                  fontSize: "14px",
                  cursor: isLoading ? "not-allowed" : "pointer",
                  opacity: isLoading ? 0.5 : 1,
                }}
              >
                Clear
              </button>
            </div>

            {apiError && (
              <p
                role="alert"
                style={{
                  fontFamily: FONT_SANS,
                  fontSize: "13px",
                  color: "#E5534B",
                  margin: "12px 0 0",
                }}
              >
                {apiError}
              </p>
            )}
          </div>
        )}

        {/* ── STATE 3: Published ────────────────────────────────────── */}
        {state === "published" && (
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "8px",
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  backgroundColor: "#22c55e20",
                  color: "#22c55e",
                  fontSize: "14px",
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                ✓
              </span>
              <h3
                style={{
                  fontFamily: FONT_HEADING,
                  fontWeight: 800,
                  fontSize: "1.0625rem",
                  color: "var(--color-text-primary)",
                  margin: 0,
                }}
              >
                {publishedCount} task{publishedCount !== 1 ? "s" : ""} published for{" "}
                <span style={{ color: "var(--color-cta-primary)" }}>{repoName}</span>
              </h3>
            </div>

            <p
              style={{
                fontFamily: FONT_SANS,
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                margin: "0 0 18px",
                lineHeight: 1.55,
              }}
            >
              They will now appear in the discovery grid for contributors to find.
            </p>

            <button
              type="button"
              onClick={handleReset}
              style={{
                background: "none",
                border: "none",
                fontFamily: FONT_SANS,
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--color-cta-primary)",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
                textDecorationColor: "transparent",
                transition: "text-decoration-color 150ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.textDecorationColor = "var(--color-cta-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.textDecorationColor = "transparent";
              }}
            >
              Generate for another repo →
            </button>
          </div>
        )}
      </div>
    </>
  );
}
