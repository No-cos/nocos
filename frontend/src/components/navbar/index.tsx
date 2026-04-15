"use client";

/**
 * Navbar component — top navigation bar for Nocos.
 *
 * Features:
 * - Nocos wordmark (Plus Jakarta Sans, purple) on the left
 * - Centre nav links: Tasks, Resources, Events, Blog
 * - Right side: Sign In link + dark mode toggle (sun/moon icon)
 * - Becomes sticky on scroll with a subtle border-bottom
 * - Collapses to hamburger menu on mobile
 * - Dark mode state is lifted from useDarkMode — all colours via CSS variables,
 *   no hardcoded hex values anywhere in this component
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useDarkMode } from "@/hooks/useDarkMode";
import type { NavbarProps } from "./types";

const DEFAULT_LINKS: { label: string; href: string }[] = [
  { label: "Tasks", href: "/" },
  { label: "Resources", href: "/resources" },
  { label: "Events", href: "/events" },
  { label: "Blog", href: "/blog" },
];

export function Navbar({ links = DEFAULT_LINKS }: NavbarProps) {
  const { theme, toggleTheme } = useDarkMode();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // Add border-bottom once the user scrolls past 8px — keeps the navbar
  // clean at the top but provides visual separation when content is beneath it.
  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > 8);
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close mobile menu when viewport widens past tablet breakpoint
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 768) setMenuOpen(false);
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        backgroundColor: "var(--color-bg)",
        borderBottom: scrolled
          ? "1px solid var(--color-border)"
          : "1px solid transparent",
        transition: "border-color 150ms ease, background 200ms ease",
      }}
    >
      <nav
        style={{
          maxWidth: "var(--content-max-width)",
          margin: "0 auto",
          padding: "0 24px",
          height: "60px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "24px",
        }}
        aria-label="Main navigation"
      >
        {/* ── Wordmark ───────────────────────────────────────────────── */}
        <Link
          href="/"
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: "1.25rem",
            color: "var(--color-cta-primary)",
            textDecoration: "none",
            letterSpacing: "-0.02em",
            flexShrink: 0,
          }}
          aria-label="Nocos home"
        >
          Nocos
        </Link>

        {/* ── Centre links (desktop) ─────────────────────────────────── */}
        <ul
          style={{
            display: "flex",
            gap: "32px",
            listStyle: "none",
            margin: 0,
            padding: 0,
          }}
          className="nav-links-desktop"
        >
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 500,
                  fontSize: "0.9375rem",
                  color: "var(--color-text-secondary)",
                  textDecoration: "none",
                  transition: "color 150ms ease",
                }}
                onMouseEnter={(e) =>
                  ((e.target as HTMLElement).style.color =
                    "var(--color-text-primary)")
                }
                onMouseLeave={(e) =>
                  ((e.target as HTMLElement).style.color =
                    "var(--color-text-secondary)")
                }
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* ── Right side: Sign In + dark mode toggle ─────────────────── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            flexShrink: 0,
          }}
        >
          {/* Sign In — hidden for now, re-enable when auth is ready */}
          {/* <Link href="/signin" ...>Sign In</Link> */}

          {/* Dark mode toggle — sun in dark mode, moon in light mode */}
          <button
            onClick={toggleTheme}
            aria-label={
              theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
            }
            style={{
              background: "none",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              padding: "6px 8px",
              cursor: "pointer",
              fontSize: "1rem",
              lineHeight: 1,
              color: "var(--color-text-secondary)",
              transition: "border-color 150ms ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          {/* Hamburger — mobile only */}
          <button
            onClick={() => setMenuOpen((o) => !o)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            className="hamburger-btn"
            style={{
              background: "none",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              padding: "6px 8px",
              cursor: "pointer",
              color: "var(--color-text-primary)",
              fontSize: "1.125rem",
              lineHeight: 1,
            }}
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </nav>

      {/* ── Mobile menu ───────────────────────────────────────────────── */}
      {menuOpen && (
        <div
          id="mobile-menu"
          style={{
            backgroundColor: "var(--color-bg)",
            borderTop: "1px solid var(--color-border)",
            padding: "16px 24px 24px",
          }}
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
            {links.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    display: "block",
                    padding: "10px 0",
                    fontFamily: "'Inter', sans-serif",
                    fontWeight: 500,
                    fontSize: "1rem",
                    color: "var(--color-text-primary)",
                    textDecoration: "none",
                    borderBottom: "1px solid var(--color-border)",
                  }}
                >
                  {link.label}
                </Link>
              </li>
            ))}
            {/* Sign In — hidden for now, re-enable when auth is ready */}
            {/* <li style={{ paddingTop: "12px" }}><Link href="/signin">Sign In</Link></li> */}
          </ul>
        </div>
      )}

    </header>
  );
}
