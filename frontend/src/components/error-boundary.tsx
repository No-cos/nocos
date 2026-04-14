"use client";

/**
 * ErrorBoundary — catches unexpected React render errors and shows a
 * friendly fallback UI instead of a blank/broken page.
 *
 * React error boundaries must be class components. This one accepts an
 * optional `fallback` prop so pages can supply a custom recovery UI.
 * When no fallback is provided, a default message with a Refresh button
 * is shown.
 *
 * Raw error messages and stack traces are NEVER shown to users — they
 * are only logged to the console for debugging (SKILLS.md §6).
 *
 * Usage:
 *   <ErrorBoundary>
 *     <MyPage />
 *   </ErrorBoundary>
 *
 *   <ErrorBoundary fallback={<p>Custom error UI</p>}>
 *     <MyPage />
 *   </ErrorBoundary>
 */

import React from "react";

interface ErrorBoundaryProps {
  /** Content to render when no error has occurred. */
  children: React.ReactNode;
  /**
   * Optional custom fallback UI. When omitted, the default friendly
   * message with a Refresh button is shown.
   */
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  /**
   * Update state so the next render shows the fallback UI.
   * Called by React when a child component throws during rendering.
   */
  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  /**
   * Log the error internally for debugging.
   * Raw errors are never surfaced to the user — only the friendly fallback.
   */
  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // In production this would feed into an error tracking service
    // (e.g. Sentry). For now, console.error is sufficient.
    console.error(
      "[ErrorBoundary] Uncaught render error:",
      error,
      info.componentStack
    );
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <DefaultFallback
          onRetry={() => this.setState({ hasError: false })}
        />
      );
    }

    return this.props.children;
  }
}

// ── Default fallback UI ───────────────────────────────────────────────────────

interface DefaultFallbackProps {
  /** Called when the user clicks "Try again" — resets the error state. */
  onRetry: () => void;
}

/**
 * DefaultFallback — the friendly error message shown when an unexpected
 * React render error occurs.
 *
 * Styled using CSS variables only so light/dark mode works automatically.
 * Never shows technical error details to the user.
 */
function DefaultFallback({ onRetry }: DefaultFallbackProps) {
  return (
    <div
      style={{
        minHeight: "40vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        backgroundColor: "var(--color-bg)",
      }}
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
        Something went wrong.
      </p>
      <p
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "0.9375rem",
          color: "var(--color-text-secondary)",
          marginBottom: "28px",
          lineHeight: 1.6,
        }}
      >
        Try refreshing the page. If the problem persists, check back soon.
      </p>
      <button
        onClick={onRetry}
        style={{
          padding: "10px 24px",
          backgroundColor: "var(--color-cta-primary)",
          color: "#ffffff",
          fontFamily: "'Inter', sans-serif",
          fontWeight: 600,
          fontSize: "0.9375rem",
          borderRadius: "8px",
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
  );
}
