"use client";

/**
 * Navbar component — top navigation bar for Nocos.
 *
 * Features:
 * - Nocos wordmark (logo image) on the left
 * - Centre nav links: Home, Resources, Events, Blog (desktop)
 * - Right side: dark mode toggle (sun/moon icon) + hamburger (mobile)
 * - Becomes sticky on scroll with a subtle border-bottom
 * - Mobile menu: absolute dropdown panel, closes on link click / outside click / route change
 * - Hamburger animates to ✕ when menu is open
 * - All colours via CSS variables, no hardcoded hex values
 */

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useDarkMode } from "@/hooks/useDarkMode";
import type { NavbarProps } from "./types";

const DEFAULT_LINKS: { label: string; href: string }[] = [
  { label: "Home", href: "/" },
  { label: "Resources", href: "/resources" },
  { label: "Events", href: "/events" },
  { label: "Blog", href: "/blog" },
];

export function Navbar({ links = DEFAULT_LINKS }: NavbarProps) {
  const { theme, toggleTheme } = useDarkMode();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const menuRef = useRef<HTMLDivElement>(null);

  // Add border-bottom once the user scrolls past 8px
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

  // Close mobile menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Close mobile menu when clicking outside
  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  const bgColor =
    theme === "dark"
      ? "rgba(12, 12, 12, 0.90)"
      : "rgba(255, 255, 255, 0.90)";

  return (
    <header
      ref={menuRef}
      className={scrolled ? "navbar-scrolled" : undefined}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        backgroundColor: bgColor,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--color-border)",
        transition: "box-shadow 150ms ease, background 200ms ease",
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
          style={{ flexShrink: 0, display: "flex", alignItems: "center" }}
          aria-label="Nocos home"
        >
          <Image
            src="/nocos_logo.png"
            alt="Nocos"
            width={59}
            height={24}
            style={{ objectFit: "contain", display: "block" }}
            priority
          />
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

        {/* ── Right side: dark mode toggle + hamburger ───────────────── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            flexShrink: 0,
          }}
        >
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

          {/* Hamburger — mobile only, shown via CSS */}
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
              padding: "6px 10px",
              cursor: "pointer",
              color: "var(--color-text-primary)",
              fontSize: "1.125rem",
              lineHeight: 1,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Animated icon: hamburger ↔ close */}
            <span
              aria-hidden="true"
              style={{
                display: "inline-block",
                transition: "transform 200ms ease, opacity 200ms ease",
                transform: menuOpen ? "rotate(90deg)" : "rotate(0deg)",
              }}
            >
              {menuOpen ? "✕" : "☰"}
            </span>
          </button>
        </div>
      </nav>

      {/* ── Mobile menu dropdown ──────────────────────────────────────── */}
      {menuOpen && (
        <>
          {/* Backdrop — clicking it closes the menu */}
          <div
            aria-hidden="true"
            onClick={() => setMenuOpen(false)}
            style={{
              position: "fixed",
              inset: 0,
              top: "60px",
              zIndex: 40,
              background: "transparent",
            }}
          />

          {/* Menu panel */}
          <div
            id="mobile-menu"
            role="dialog"
            aria-label="Mobile navigation"
            style={{
              position: "absolute",
              top: "100%",
              left: 0,
              right: 0,
              zIndex: 50,
              backgroundColor: "var(--color-surface)",
              borderBottom: "1px solid var(--color-border)",
              padding: "16px 24px 24px",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
            }}
          >
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {links.map((link, i) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    style={{
                      display: "block",
                      width: "100%",
                      padding: "12px 0",
                      fontFamily: "'Inter', sans-serif",
                      fontSize: "15px",
                      fontWeight: 500,
                      color: "var(--color-text-primary)",
                      textDecoration: "none",
                      borderBottom:
                        i < links.length - 1
                          ? "1px solid var(--color-border)"
                          : "none",
                    }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </header>
  );
}
