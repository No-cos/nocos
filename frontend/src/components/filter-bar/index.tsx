"use client";

/**
 * FilterBar component — tag pill filter row above the issue discovery grid.
 *
 * Renders an "All" reset pill followed by one Tag pill for each contribution
 * type. Multiple types can be selected simultaneously. Clicking a selected
 * type deselects it; clicking "All" resets all filters.
 *
 * On mobile the bar scrolls horizontally without wrapping so it never
 * pushes content down (SKILLS.md §11).
 *
 * @param activeTypes - Array of currently selected type strings
 * @param onChange    - Called with the new activeTypes array on every change
 */

import { Tag, ALL_CONTRIBUTION_TYPES } from "@/components/ui/tag";
import { formatContributionType } from "@/lib/utils";
import type { FilterBarProps } from "./types";

export function FilterBar({
  activeTypes,
  onChange,
  bountyOnly = false,
  onBountyChange,
}: FilterBarProps) {
  const allSelected = activeTypes.length === 0 && !bountyOnly;

  function handleAll() {
    // "All" resets both type filters and the bounty toggle
    onChange([]);
    onBountyChange?.(false);
  }

  function handleBounty() {
    onBountyChange?.(!bountyOnly);
  }

  function handleType(type: string) {
    if (activeTypes.includes(type)) {
      // Deselect — remove from array
      const next = activeTypes.filter((t) => t !== type);
      onChange(next);
    } else {
      // Select — add to array
      onChange([...activeTypes, type]);
    }
  }

  return (
    <div
      role="group"
      aria-label="Filter issues by contribution type"
      style={{
        display: "flex",
        gap: "8px",
        overflowX: "auto",
        // Hide scrollbar visually on all browsers while keeping functionality
        scrollbarWidth: "none",
        paddingBottom: "4px",
        // Prevent flex items from shrinking so tags don't get squished on mobile
        flexWrap: "nowrap",
      }}
    >
      {/* All pill — neutral border when inactive, primary color when active */}
      <button
        type="button"
        onClick={handleAll}
        aria-pressed={allSelected}
        style={{
          display: "inline-flex",
          alignItems: "center",
          padding: "5px 14px",
          backgroundColor: allSelected
            ? "var(--color-cta-primary)"
            : "var(--color-surface)",
          color: allSelected ? "#ffffff" : "var(--color-text-primary)",
          border: `1.5px solid ${
            allSelected ? "var(--color-cta-primary)" : "var(--color-border)"
          }`,
          borderRadius: "999px",
          fontFamily: "'Inter', sans-serif",
          fontWeight: 500,
          fontSize: "13px",
          cursor: "pointer",
          whiteSpace: "nowrap",
          flexShrink: 0,
          transition: "background 150ms ease, color 150ms ease",
        }}
      >
        All
      </button>

      {/* Bounties pill — independent toggle, not a contribution type */}
      <button
        type="button"
        onClick={handleBounty}
        aria-pressed={bountyOnly}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          padding: "5px 14px",
          backgroundColor: bountyOnly
            ? "var(--color-bounty-bg)"
            : "var(--color-surface)",
          color: bountyOnly
            ? "var(--color-bounty-text)"
            : "var(--color-text-primary)",
          border: `1.5px solid ${
            bountyOnly
              ? "var(--color-bounty-border)"
              : "var(--color-border)"
          }`,
          borderRadius: "999px",
          fontFamily: "'Inter', sans-serif",
          fontWeight: 600,
          fontSize: "13px",
          cursor: "pointer",
          whiteSpace: "nowrap",
          flexShrink: 0,
          transition: "background 150ms ease, color 150ms ease, border-color 150ms ease",
        }}
      >
        💰 Bounties
      </button>

      {/* One pill per contribution type */}
      {ALL_CONTRIBUTION_TYPES.map((type) => {
        const isSelected = activeTypes.includes(type);
        return (
          <div key={type} style={{ flexShrink: 0 }}>
            <Tag
              type={type}
              label={formatContributionType(type)}
              size="md"
              selected={isSelected}
              filterMode={true}
              onClick={() => handleType(type)}
            />
          </div>
        );
      })}

    </div>
  );
}
