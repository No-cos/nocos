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

export function FilterBar({ activeTypes, onChange }: FilterBarProps) {
  const allSelected = activeTypes.length === 0;

  function handleAll() {
    // "All" resets to empty array — the grid interprets [] as no filter
    onChange([]);
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
              onClick={() => handleType(type)}
            />
          </div>
        );
      })}

    </div>
  );
}
