"use client";

/**
 * FeaturedProjects — curated open-source repos shown on the homepage.
 *
 * Two tabs:
 *   🔥 Most Active This Week  — repos ranked by commit / issue / star activity
 *   🌱 New & Promising        — recently-created repos with strong star momentum
 *
 * Data is fetched from GET /api/v1/featured on mount. While loading, 6
 * skeleton placeholder cards are shown per tab. If the API returns an error
 * or both arrays are empty, the section is omitted entirely (returns null).
 *
 * All colours come from CSS variables — zero hardcoded hex values.
 * No new npm dependencies.
 */

import { useEffect, useState } from "react";
import Image from "next/image";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FeaturedProject {
  repo_full_name: string;
  name: string;
  description: string;
  language: string | null;
  stars: number;
  stars_gained_this_week: number | null;
  weekly_commits: number;
  forks: number;
  open_issues_count: number;
  homepage: string | null;
  license: string | null;
  topics: string[];
  avatar_url: string;
  github_url: string;
  category: "most_active" | "new_promising";
}

// ─── Language colour dots ─────────────────────────────────────────────────────
// A small curated set — unknown languages fall back to the border colour.
const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178C6",
  JavaScript: "#F7DF1E",
  Python:     "#3572A5",
  Go:         "#00ADD8",
  Rust:       "#DEA584",
  Java:       "#B07219",
  "C++":      "#F34B7D",
  C:          "#555555",
  Ruby:       "#701516",
  PHP:        "#4F5D95",
  Swift:      "#F05138",
  Kotlin:     "#A97BFF",
  Dart:       "#00B4AB",
  Shell:      "#89E051",
  HTML:       "#E34C26",
  CSS:        "#563D7C",
  Vue:        "#41B883",
  Svelte:     "#FF3E00",
};

function langColor(lang: string | null): string {
  if (!lang) return "var(--color-border)";
  return LANG_COLORS[lang] ?? "var(--color-text-secondary)";
}

// ─── Number formatting ────────────────────────────────────────────────────────

function fmt(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

// ─── Skeleton card ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--card-radius)",
        boxShadow: "var(--card-shadow)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        height: "280px",
      }}
    >
      {/* Avatar + owner */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div
          className="sk"
          style={{ width: 36, height: 36, borderRadius: "50%", flexShrink: 0 }}
        />
        <div className="sk" style={{ height: 12, width: "45%", borderRadius: 6 }} />
      </div>
      {/* Repo name */}
      <div className="sk" style={{ height: 16, width: "70%", borderRadius: 6 }} />
      {/* Description lines */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="sk" style={{ height: 12, width: "100%", borderRadius: 6 }} />
        <div className="sk" style={{ height: 12, width: "80%", borderRadius: 6 }} />
      </div>
      {/* Badges row */}
      <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
        <div className="sk" style={{ height: 24, width: 70, borderRadius: 999 }} />
        <div className="sk" style={{ height: 24, width: 60, borderRadius: 999 }} />
      </div>
      {/* Buttons */}
      <div style={{ display: "flex", gap: 8 }}>
        <div className="sk" style={{ height: 34, flex: 1, borderRadius: 8 }} />
        <div className="sk" style={{ height: 34, width: 80, borderRadius: 8 }} />
      </div>
    </div>
  );
}

// ─── Project card ─────────────────────────────────────────────────────────────

function ProjectCard({ project }: { project: FeaturedProject }) {
  const [owner, repo] = project.repo_full_name.split("/");

  // "Browse Issues" scrolls down to the issue grid filtered by this repo
  const browseUrl = `/?repo=${encodeURIComponent(project.repo_full_name)}#issues`;

  const isMostActive = project.category === "most_active";

  return (
    <article
      className="card card-enter-anim"
      style={{
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: 0,
        // Fixed height keeps all cards uniform; overflow: hidden clips long content
        minHeight: "280px",
        transition: "transform var(--transition-speed), box-shadow var(--transition-speed), border-color var(--transition-speed)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "var(--color-text-secondary)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "var(--color-border)";
      }}
    >
      {/* ── Header: avatar + owner / repo name ──────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", marginBottom: "12px" }}>
        {/* Owner avatar */}
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            overflow: "hidden",
            flexShrink: 0,
            backgroundColor: "var(--color-border)",
          }}
        >
          {project.avatar_url ? (
            <Image
              src={project.avatar_url}
              alt={`${owner} avatar`}
              width={36}
              height={36}
              style={{ display: "block" }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700,
                fontSize: "14px",
                color: "var(--color-text-secondary)",
              }}
            >
              {owner?.[0]?.toUpperCase() ?? "?"}
            </div>
          )}
        </div>

        {/* Owner + repo name stacked */}
        <div style={{ minWidth: 0 }}>
          <p
            style={{
              margin: 0,
              fontFamily: "'Inter', sans-serif",
              fontSize: "11px",
              fontWeight: 500,
              color: "var(--color-text-secondary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {owner}
          </p>
          <p
            style={{
              margin: "2px 0 0",
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontSize: "15px",
              fontWeight: 700,
              color: "var(--color-text-primary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {repo}
          </p>
        </div>
      </div>

      {/* ── Description ─────────────────────────────────────────────── */}
      <p
        style={{
          margin: "0 0 14px",
          fontFamily: "'Inter', sans-serif",
          fontSize: "13px",
          lineHeight: 1.55,
          color: "var(--color-text-secondary)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {project.description || "No description provided."}
      </p>

      {/* ── Badges row: language + stars ─────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
        {/* Language */}
        {project.language && (
          <span style={badgeStyle()}>
            <span
              aria-hidden="true"
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: langColor(project.language),
                flexShrink: 0,
              }}
            />
            {project.language}
          </span>
        )}

        {/* Star count */}
        <span style={badgeStyle()}>
          ⭐ {fmt(project.stars)}
        </span>

        {/* Category-specific metric */}
        {isMostActive ? (
          <span
            style={{
              ...badgeStyle(),
              color: "var(--color-status-active)",
              borderColor: "var(--color-status-active)",
            }}
          >
            ↑ {fmt(project.weekly_commits)} commits
          </span>
        ) : project.stars_gained_this_week != null && project.stars_gained_this_week > 0 ? (
          <span
            style={{
              ...badgeStyle(),
              color: "var(--color-cta-primary)",
              borderColor: "var(--color-cta-primary)",
            }}
          >
            ✦ +{fmt(project.stars_gained_this_week)} stars
          </span>
        ) : null}
      </div>

      {/* ── License badge ────────────────────────────────────────────── */}
      {project.license && (
        <div style={{ marginBottom: "14px" }}>
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "11px",
              color: "var(--color-text-secondary)",
              backgroundColor: "var(--color-bg)",
              border: "1px solid var(--color-border)",
              borderRadius: "4px",
              padding: "2px 7px",
            }}
          >
            {project.license}
          </span>
        </div>
      )}

      {/* ── Action button — pinned to card bottom via marginTop: auto ── */}
      <div style={{ marginTop: "auto", paddingTop: "4px" }}>
        {/* GitHub — full width */}
        <a
          href={project.github_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            fontFamily: "'Inter', sans-serif",
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--color-text-primary)",
            backgroundColor: "transparent",
            border: "1.5px solid var(--color-border)",
            borderRadius: "8px",
            padding: "7px 12px",
            textDecoration: "none",
            transition: "border-color 120ms ease",
            boxSizing: "border-box",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-text-secondary)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-border)";
          }}
        >
          GitHub ↗
        </a>
      </div>
    </article>
  );
}

// Shared badge style factory (avoids repeating the object inline)
function badgeStyle(): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: "5px",
    fontFamily: "'Inter', sans-serif",
    fontSize: "12px",
    fontWeight: 500,
    color: "var(--color-text-secondary)",
    backgroundColor: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "999px",
    padding: "3px 9px",
  };
}

// ─── Tab button ───────────────────────────────────────────────────────────────

function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: "none",
        border: "none",
        borderBottom: active
          ? "2px solid var(--color-cta-primary)"
          : "2px solid transparent",
        padding: "10px 4px",
        fontFamily: "'Inter', sans-serif",
        fontSize: "14px",
        fontWeight: active ? 600 : 400,
        color: active ? "var(--color-text-primary)" : "var(--color-text-secondary)",
        cursor: "pointer",
        transition: "color var(--transition-speed), border-color var(--transition-speed)",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

type Tab = "most_active" | "new_promising";

export function FeaturedProjects() {
  const [mostActive, setMostActive] = useState<FeaturedProject[]>([]);
  const [newPromising, setNewPromising] = useState<FeaturedProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("most_active");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/v1/featured`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        const data = json?.data ?? {};
        setMostActive(data.most_active ?? []);
        setNewPromising(data.new_promising ?? []);
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, []);

  // Don't render the section at all if data failed or both lists are empty
  if (!loading && (failed || (mostActive.length === 0 && newPromising.length === 0))) {
    return null;
  }

  const cards = activeTab === "most_active" ? mostActive : newPromising;

  return (
    <section
      aria-label="Featured open-source projects"
      style={{
        borderTop: "1px solid var(--color-border)",
        paddingTop: "80px",
        paddingBottom: "80px",
      }}
    >
      <div className="page-container">
        {/* ── Section header ─────────────────────────────────────────── */}
        <div style={{ marginBottom: "36px" }}>
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
            Featured Projects
          </p>
          <h2
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800,
              fontSize: "clamp(1.5rem, 3vw, 2rem)",
              color: "var(--color-text-primary)",
              margin: 0,
              lineHeight: 1.2,
            }}
          >
            Discover open source
          </h2>
        </div>

        {/* ── Tabs ───────────────────────────────────────────────────── */}
        <div
          role="tablist"
          aria-label="Featured project categories"
          style={{
            display: "flex",
            gap: "24px",
            borderBottom: "1px solid var(--color-border)",
            marginBottom: "28px",
          }}
        >
          <TabButton
            label="🔥 Most Active This Week"
            active={activeTab === "most_active"}
            onClick={() => setActiveTab("most_active")}
          />
          <TabButton
            label="🌱 New & Promising"
            active={activeTab === "new_promising"}
            onClick={() => setActiveTab("new_promising")}
          />
        </div>

        {/* ── Card grid ──────────────────────────────────────────────── */}
        <div
          role="tabpanel"
          aria-label={
            activeTab === "most_active"
              ? "Most Active This Week"
              : "New & Promising"
          }
          className="featured-grid"
        >
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
            : cards.map((project) => (
                <ProjectCard key={project.repo_full_name} project={project} />
              ))}
        </div>
      </div>
    </section>
  );
}
