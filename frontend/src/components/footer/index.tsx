"use client";

/**
 * Footer component — site-wide footer for Nocos.
 *
 * Layout (3 columns on desktop, stacked on mobile):
 * - Left:   Nocos wordmark + short tagline
 * - Centre: nav links (Tasks, Resources, Events, Blog, GitHub repo)
 * - Right:  social links (Twitter/X, GitHub, Discord)
 * - Bottom bar: copyright + license notice
 *
 * All colours via CSS variables. External links open in new tab with
 * rel="noopener noreferrer" for security.
 */

import Link from "next/link";
import { useInView } from "@/hooks/use-in-view";

const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Resources", href: "/resources" },
  { label: "Events", href: "/events" },
  { label: "Blog", href: "/blog" },
  { label: "GitHub", href: "https://github.com/No-cos/nocos", external: true },
];

const SOCIAL_LINKS = [
  {
    label: "Twitter / X",
    href: "https://twitter.com/nocosdev",
    icon: "𝕏",
  },
  {
    label: "GitHub",
    href: "https://github.com/No-cos/nocos",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.54-1.38-1.33-1.74-1.33-1.74-1.09-.74.08-.73.08-.73 1.2.08 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49.99.11-.78.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.12-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.04.13 3 .4 2.28-1.55 3.29-1.23 3.29-1.23.66 1.66.24 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.48 5.92.43.37.82 1.1.82 2.22v3.29c0 .32.21.7.83.58C20.56 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12z"/>
      </svg>
    ),
  },
  {
    label: "Discord",
    href: "https://discord.gg/nocos",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.04.03.052a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
      </svg>
    ),
  },
];

export function Footer() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <footer
      ref={ref}
      className={`reveal${inView ? " visible" : ""}`}
      style={{
        backgroundColor: "var(--color-bg)",
        borderTop: "1px solid var(--color-border)",
      }}
    >
      {/* Main footer grid */}
      <div
        style={{
          maxWidth: "var(--content-max-width)",
          margin: "0 auto",
          padding: "48px 24px 40px",
        }}
      >
        <div className="footer-grid">
          {/* ── Left: wordmark + tagline ───────────────────────────────── */}
          <div>
            <Link
              href="/"
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 800,
                fontSize: "1.125rem",
                color: "var(--color-cta-primary)",
                textDecoration: "none",
                letterSpacing: "-0.02em",
              }}
            >
              Nocos
            </Link>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                lineHeight: 1.6,
                marginTop: "8px",
                maxWidth: "200px",
              }}
            >
              Discover and contribute to open source without technical hassle.
            </p>
          </div>

          {/* ── Centre: nav links ──────────────────────────────────────── */}
          <nav aria-label="Footer navigation">
            <ul
              style={{
                listStyle: "none",
                margin: 0,
                padding: 0,
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  {link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={footerLinkStyle}
                    >
                      {link.label}
                    </a>
                  ) : (
                    <Link href={link.href} style={footerLinkStyle}>
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>

          {/* ── Right: social links ────────────────────────────────────── */}
          <div>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: "14px",
              }}
            >
              Community
            </p>
            <ul
              style={{
                listStyle: "none",
                margin: 0,
                padding: 0,
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {SOCIAL_LINKS.map((social) => (
                <li key={social.href}>
                  <a
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={social.label}
                    style={{
                      ...footerLinkStyle,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    {social.icon}
                    {social.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div
        style={{
          borderTop: "1px solid var(--color-border)",
          padding: "16px 24px",
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "12px",
            color: "var(--color-text-secondary)",
            margin: 0,
          }}
        >
          © 2025 Nocos. Open source.{" "}
          <a
            href="https://github.com/No-cos/nocos/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--color-text-secondary)", textDecoration: "underline" }}
          >
            MIT License
          </a>
          .
        </p>
      </div>

    </footer>
  );
}

const footerLinkStyle: React.CSSProperties = {
  fontFamily: "'Inter', sans-serif",
  fontSize: "14px",
  color: "var(--color-text-secondary)",
  textDecoration: "none",
  transition: "color 150ms ease",
};
