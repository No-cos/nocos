"use client";

/**
 * Hero component — the first section visitors see on the landing page.
 *
 * Contains the headline, sub-headline, and two CTA buttons:
 * - "Find Tasks →"  filled purple (var(--color-cta-primary))
 * - "Post Tasks"    filled cream  (var(--color-cta-secondary))
 *
 * The ASCII globe is rendered as a decorative background layer:
 * - position: absolute, fills the section, pointer-events: none
 * - opacity: 0.35 so it reads as texture, not competing with the headline
 * - mask-image fades it out toward the bottom so it blends into the marquee
 *
 * Responsive: buttons stack vertically below 480px.
 * All colours via CSS variables — no hardcoded hex values.
 */

import Link from "next/link";
import { GlobeAnimation } from "@/components/globe";

export function Hero() {
  return (
    <section
      style={{
        backgroundColor: "var(--color-bg)",
        padding: "150px 24px 150px",
        textAlign: "center",
        position: "relative",
        overflowX: "visible",
        overflowY: "hidden",
      }}
      aria-labelledby="hero-headline"
    >
      {/* ── Globe background layer ─────────────────────────────────────── */}
      {/* Outer wrapper: 140vw wide, centred — bleeds equally off left/right.
          alignItems: flex-start so the globe text starts at the top of the
          section, ensuring the rounded top arc of the sphere is visible. */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "140vw",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "center",
          zIndex: 0,
          pointerEvents: "none",
        }}
      >
        {/* Inner wrapper: carries opacity + mask (on inner, not overflow container).
            No height constraint — the globe text (~90vh tall) fills naturally;
            the section's overflowY: hidden clips the bottom,
            the mask fades it out before the hard clip. */}
        <div
          style={{
            opacity: 0.35,
            pointerEvents: "none",
            maskImage:
              "linear-gradient(to bottom, black 0%, black 55%, transparent 100%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black 0%, black 55%, transparent 100%)",
          }}
        >
          <GlobeAnimation />
        </div>
      </div>

      {/* ── Hero text content — sits above the globe ───────────────────── */}
      <div
        style={{
          maxWidth: "720px",
          margin: "0 auto",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Headline */}
        <h1
          id="hero-headline"
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(2rem, 5vw, 3.25rem)",
            lineHeight: 1.15,
            letterSpacing: "-0.03em",
            color: "var(--color-text-primary)",
            margin: "0 0 20px",
          }}
        >
          Open source needs<br />more than <span style={{ color: "#C6C9D3" }}>code.</span>
        </h1>

        {/* Sub-headline */}
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontWeight: 400,
            fontSize: "clamp(1rem, 2.5vw, 1.125rem)",
            lineHeight: 1.65,
            color: "var(--color-text-secondary)",
            margin: "0 0 40px",
            maxWidth: "560px",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          Find non-code tasks from real open source projects.
        </p>

        {/* CTA buttons */}
        <div className="hero-ctas">
          <Link
            href="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "13px 28px",
              backgroundColor: "var(--color-cta-primary)",
              color: "#ffffff",
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              fontSize: "0.9375rem",
              textDecoration: "none",
              borderRadius: "10px",
              transition: "opacity 150ms ease",
              border: "none",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.opacity = "0.88")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.opacity = "1")
            }
          >
            Find Tasks →
          </Link>

          <Link
            href="/post"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "13px 28px",
              backgroundColor: "var(--color-cta-secondary)",
              color: "var(--color-cta-secondary-text)",
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              fontSize: "0.9375rem",
              textDecoration: "none",
              borderRadius: "10px",
              transition: "opacity 150ms ease",
              border: "none",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.opacity = "0.88")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.opacity = "1")
            }
          >
            Post Tasks
          </Link>
        </div>
      </div>
    </section>
  );
}
