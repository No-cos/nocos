"use client";

/**
 * Landing page (/) — the Nocos discovery home.
 *
 * Composes all Phase 3 components in order:
 *   Navbar → Hero → CategoryMarquee → [FilterBar + SearchBar] →
 *   IssueGrid → SubscribeSection → Footer
 *
 * Filter and search state lives here so FilterBar, SearchBar, and IssueGrid
 * share the same values without an extra state management layer.
 *
 * Dark mode is handled by the Navbar (via useDarkMode) which toggles the
 * "dark" class on <html>. All components respond via CSS variables.
 */

import { useState } from "react";
import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { StatsBar } from "@/components/stats-bar";
import { CategoryMarquee } from "@/components/marquee";
import { FilterBar } from "@/components/filter-bar";
import { SearchBar } from "@/components/search-bar";
import { IssueGrid } from "@/components/issue-grid";
import { FeaturedProjects } from "@/components/featured-projects";
import { SubscribeSection } from "@/components/subscribe-section";
import { Footer } from "@/components/footer";

export default function HomePage() {
  // Filter and search state is lifted here so FilterBar, SearchBar, and
  // IssueGrid all read from and write to the same values.
  const [activeTypes, setActiveTypes] = useState<string[]>([]);
  const [search, setSearch] = useState("");

  function handleTypesChange(types: string[]) {
    setActiveTypes(types);
    // Reset search when filters change to avoid confusing combined results
    // intentionally NOT resetting search — user may want both active
  }

  return (
    <>
      {/* ── Navigation ─────────────────────────────────────────────── */}
      <Navbar />

      <main>
        {/* ── Hero ────────────────────────────────────────────────── */}
        <Hero />

        {/* ── Live stats ──────────────────────────────────────────── */}
        <StatsBar />

        {/* ── Category Marquee ────────────────────────────────────── */}
        <CategoryMarquee />

        {/* ── Discovery section ───────────────────────────────────── */}
        <section
          className="page-container"
          style={{ paddingTop: "100px", paddingBottom: "100px" }}
          aria-label="Issue discovery"
        >
          {/* Filter bar + search bar — side by side on desktop, stacked on mobile */}
          <div className="discovery-controls">
            <div style={{ flex: 1, minWidth: 0 }}>
              <FilterBar
                activeTypes={activeTypes}
                onChange={handleTypesChange}
              />
            </div>
            <SearchBar value={search} onChange={setSearch} />
          </div>

          {/* Issue count / active filter summary — helps orientation */}
          {(activeTypes.length > 0 || search) && (
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                margin: "12px 0 0",
              }}
            >
              {activeTypes.length > 0 &&
                `Filtering by: ${activeTypes.join(", ")}`}
              {activeTypes.length > 0 && search && " · "}
              {search && `Searching for "${search}"`}
              <button
                onClick={() => {
                  setActiveTypes([]);
                  setSearch("");
                }}
                style={{
                  marginLeft: "12px",
                  background: "none",
                  border: "none",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "13px",
                  color: "var(--color-cta-primary)",
                  cursor: "pointer",
                  padding: 0,
                  textDecoration: "underline",
                }}
              >
                Clear all
              </button>
            </p>
          )}

          {/* Issue grid — wired to filter + search state */}
          <div style={{ marginTop: "28px" }}>
            <IssueGrid activeTypes={activeTypes} search={search} />
          </div>
        </section>

        {/* ── Featured Projects ───────────────────────────────────── */}
        <FeaturedProjects />

        {/* ── Subscribe Section ───────────────────────────────────── */}
        <SubscribeSection />
      </main>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <Footer />

    </>
  );
}
