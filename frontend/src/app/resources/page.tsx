"use client";

/**
 * Resources — Coming Soon page.
 * Full-viewport centred layout matching the Nocos design system.
 */

import Link from "next/link";
import { Navbar } from "@/components/navbar";

export default function ResourcesPage() {
  return (
    <>
      <Navbar />
      <main
        style={{
          minHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "40px 24px",
          backgroundColor: "var(--color-bg)",
        }}
      >
        {/* Coming Soon badge */}
        <span
          style={{
            display: "inline-block",
            border: "1.5px solid var(--color-cta-primary)",
            color: "var(--color-cta-primary)",
            fontFamily: "'Inter', sans-serif",
            fontSize: "12px",
            fontWeight: 600,
            borderRadius: "999px",
            padding: "4px 14px",
            marginBottom: "24px",
          }}
        >
          Coming Soon
        </span>

        <h1
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(2rem, 5vw, 3.5rem)",
            color: "var(--color-text-primary)",
            margin: "0 0 16px",
          }}
        >
          Coming Soon
        </h1>

        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "1rem",
            lineHeight: 1.7,
            color: "var(--color-text-secondary)",
            maxWidth: "480px",
            margin: "0 0 36px",
          }}
        >
          Access a rich open source library curated for non-code contributors —
          guides, templates, and tools to help you contribute with confidence.
        </p>

        <Link
          href="/"
          style={{
            display: "inline-block",
            backgroundColor: "var(--color-cta-primary)",
            color: "#FFFFFF",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "0.9375rem",
            padding: "12px 28px",
            borderRadius: "10px",
            textDecoration: "none",
            transition: "opacity 150ms ease",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "0.88")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLElement).style.opacity = "1")
          }
        >
          Return to Home
        </Link>
      </main>
    </>
  );
}
