/**
 * ProjectAbout component — renders the "About this project" section on the
 * task detail page.
 *
 * Layout (top to bottom):
 * - Section label: "ABOUT THIS PROJECT" (uppercase, muted, letter-spaced)
 * - Avatar (40×40 circle) + project name (H3) side by side
 * - Project description paragraph
 * - Website link (if present)
 * - Social links row (renders only links that exist in social_links)
 * - Activity indicator: colored dot + "Active — last commit 3 days ago"
 *
 * All colours via CSS variables only — no hardcoded hex values.
 *
 * @param project - Full Project object from the Nocos API (includes social_links,
 *                  activity_status, last_commit_date)
 */

import Image from "next/image";
import { getActivityColor, relativeTime } from "@/lib/utils";
import type { Project } from "@/lib/api";

interface ProjectAboutProps {
  project: Project;
}

// ── Activity label map ────────────────────────────────────────────────────────
const ACTIVITY_LABELS: Record<string, string> = {
  active: "Active",
  slow: "Slow",
  inactive: "Inactive",
};

// ── Social link definitions ───────────────────────────────────────────────────
// Each entry maps a social_links key to a human label and SVG icon path.
const SOCIAL_DEFS: Array<{
  key: keyof Project["social_links"];
  label: string;
  icon: React.ReactNode;
}> = [
  {
    key: "github",
    label: "GitHub",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
      </svg>
    ),
  },
  {
    key: "twitter",
    label: "Twitter / X",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    key: "discord",
    label: "Discord",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
      </svg>
    ),
  },
  {
    key: "slack",
    label: "Slack",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
      </svg>
    ),
  },
  {
    key: "linkedin",
    label: "LinkedIn",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
      </svg>
    ),
  },
  {
    key: "youtube",
    label: "YouTube",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
  },
];

export function ProjectAbout({ project }: ProjectAboutProps) {
  const activityColor = getActivityColor(project.activity_status);
  const activityLabel = ACTIVITY_LABELS[project.activity_status] ?? project.activity_status;
  const lastCommitLabel = project.last_commit_date
    ? `last commit ${relativeTime(project.last_commit_date)}`
    : null;

  // Only render social links that have a non-null, non-empty value
  const visibleSocials = SOCIAL_DEFS.filter((def) => {
    const val = project.social_links[def.key];
    return val && val.trim() !== "";
  });

  return (
    <section aria-labelledby="about-project-label">
      {/* Section label */}
      <p
        id="about-project-label"
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--color-text-secondary)",
          margin: "0 0 20px",
        }}
      >
        About this project
      </p>

      {/* Avatar + project name */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            overflow: "hidden",
            flexShrink: 0,
            backgroundColor: "var(--color-border)",
          }}
        >
          {project.avatar_url ? (
            <Image
              src={project.avatar_url}
              alt={`${project.name} avatar`}
              width={40}
              height={40}
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
                fontSize: "16px",
                color: "var(--color-text-secondary)",
              }}
            >
              {project.name[0]?.toUpperCase() ?? "?"}
            </div>
          )}
        </div>

        <h3
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "1.125rem",
            color: "var(--color-text-primary)",
            margin: 0,
          }}
        >
          {project.name}
        </h3>
      </div>

      {/* Description */}
      {project.description && (
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "0.9375rem",
            lineHeight: 1.7,
            color: "var(--color-text-secondary)",
            margin: "0 0 20px",
          }}
        >
          {project.description}
        </p>
      )}

      {/* Website link */}
      {project.website_url && (
        <a
          href={project.website_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontFamily: "'Inter', sans-serif",
            fontSize: "13px",
            color: "var(--color-cta-primary)",
            textDecoration: "none",
            marginBottom: "20px",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLElement).style.textDecoration = "underline")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLElement).style.textDecoration = "none")
          }
        >
          {/* Globe icon */}
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          {project.website_url.replace(/^https?:\/\//, "")}
        </a>
      )}

      {/* Social links row */}
      {visibleSocials.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "8px",
            marginBottom: "20px",
          }}
        >
          {visibleSocials.map((def) => {
            const url = project.social_links[def.key] as string;
            return (
              <a
                key={def.key}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${project.name} on ${def.label}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "34px",
                  height: "34px",
                  borderRadius: "8px",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-secondary)",
                  textDecoration: "none",
                  transition: "color 150ms ease, border-color 150ms ease",
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
                {def.icon}
              </a>
            );
          })}
        </div>
      )}

      {/* Activity indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
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
            fontSize: "13px",
            color: "var(--color-text-secondary)",
          }}
        >
          {activityLabel}
          {lastCommitLabel && (
            <span style={{ color: "var(--color-text-secondary)" }}>
              {" "}— {lastCommitLabel}
            </span>
          )}
        </span>
      </div>
    </section>
  );
}
