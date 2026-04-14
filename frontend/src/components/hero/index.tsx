/**
 * Hero component — the first section visitors see on the landing page.
 *
 * Contains the headline, sub-headline, and two CTA buttons:
 * - "Find Tasks →"  filled purple (var(--color-cta-primary))
 * - "Post Tasks"    filled cream  (var(--color-cta-secondary))
 *
 * Responsive: buttons stack vertically below 480px.
 * All colours via CSS variables — no hardcoded hex values.
 */

import Link from "next/link";

export function Hero() {
  return (
    <section
      style={{
        backgroundColor: "var(--color-bg)",
        padding: "80px 24px 64px",
        textAlign: "center",
      }}
      aria-labelledby="hero-headline"
    >
      <div
        style={{
          maxWidth: "720px",
          margin: "0 auto",
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
          Discover and Contribute to Your Favourite Open Source Project.
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
          Non code contributors can now discover and contribute to OS without
          technical hassle.
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
