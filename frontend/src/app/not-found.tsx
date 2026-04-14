/**
 * not-found.tsx — Next.js App Router 404 page.
 *
 * Rendered automatically by Next.js when notFound() is called or when
 * no route matches the URL. Styled with design system tokens so it looks
 * consistent with the rest of the platform in both light and dark mode.
 *
 * The page is a Server Component (no "use client" directive) so it
 * renders on the server and is SEO-friendly.
 */

import Link from "next/link";

export default function NotFound() {
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
        {/* Large 404 label */}
        <p
          aria-hidden="true"
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(4rem, 15vw, 7rem)",
            color: "var(--color-border)",
            lineHeight: 1,
            margin: "0 0 24px",
            letterSpacing: "-0.02em",
          }}
        >
          404
        </p>

        <h1
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(1.375rem, 4vw, 1.75rem)",
            color: "var(--color-text-primary)",
            margin: "0 0 12px",
          }}
        >
          Page not found
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
          The page you&apos;re looking for doesn&apos;t exist or may have
          been moved.
        </p>

        <Link
          href="/"
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
            textDecoration: "none",
            transition: "opacity 150ms ease",
          }}
        >
          Back to tasks →
        </Link>
      </div>
    </main>
  );
}
