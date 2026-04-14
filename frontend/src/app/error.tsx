"use client";

/**
 * error.tsx — Next.js App Router route-level error page.
 *
 * Rendered automatically by Next.js when an unhandled error occurs in a
 * route segment during server-side rendering or client-side navigation.
 *
 * Must be a Client Component ("use client") because it receives the
 * `reset` function prop from Next.js — a client-side callback that
 * re-renders the route segment to attempt recovery.
 *
 * Raw error messages and stack traces are NEVER shown to users (SKILLS.md §6).
 * The `error` prop is available for server-side logging if needed.
 *
 * @param error - The error that was thrown (available for logging, not display)
 * @param reset - Next.js-provided function to retry rendering the segment
 */

"use client";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  // Log server-side for observability — never display to the user
  if (process.env.NODE_ENV !== "production") {
    console.error("[Error page] Unhandled route error:", error);
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: "480px" }}>
        {/* Visual indicator */}
        <div
          aria-hidden="true"
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            border: "2px solid var(--color-status-inactive)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 28px",
            color: "var(--color-status-inactive)",
          }}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
            <circle cx="12" cy="12" r="10" />
          </svg>
        </div>

        <h1
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(1.375rem, 4vw, 1.75rem)",
            color: "var(--color-text-primary)",
            margin: "0 0 12px",
          }}
        >
          Something went wrong
        </h1>

        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "0.9375rem",
            lineHeight: 1.6,
            color: "var(--color-text-secondary)",
            margin: "0 0 36px",
          }}
        >
          We hit an unexpected error. Try again in a moment.
        </p>

        <button
          onClick={reset}
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "12px 28px",
            backgroundColor: "var(--color-cta-primary)",
            color: "#ffffff",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "0.9375rem",
            borderRadius: "10px",
            border: "none",
            cursor: "pointer",
            transition: "opacity 150ms ease",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "0.88")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "1")
          }
        >
          Try again
        </button>
      </div>
    </main>
  );
}
