"use client";

/**
 * SearchBar component — real-time search input for the issue discovery grid.
 *
 * Searches by project name, contribution type, and issue title. Input is
 * debounced 300ms before calling onChange so the API is not hit on every
 * keystroke. A clear button (×) appears when the input has content.
 *
 * @param value     - Controlled input value
 * @param onChange  - Called with the new search string after 300ms debounce
 * @param placeholder - Input placeholder text
 */

import { useState, useEffect, useRef } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Search tasks, projects, or types…",
}: SearchBarProps) {
  // Local state tracks the raw input; debounced updates go to onChange.
  // This keeps the input responsive while limiting API call frequency.
  const [localValue, setLocalValue] = useState(value);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync if parent resets the value externally (e.g. "All" filter reset)
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value;
    setLocalValue(next);

    // Clear any pending debounce timer before starting a new one
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onChange(next);
    }, 300);
  }

  function handleClear() {
    setLocalValue("");
    onChange("");
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }

  // Clean up timer on unmount to avoid state updates on an unmounted component
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        minWidth: "220px",
        maxWidth: "320px",
        width: "100%",
      }}
      role="search"
    >
      {/* Search icon */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          left: "12px",
          color: "var(--color-text-secondary)",
          fontSize: "14px",
          pointerEvents: "none",
        }}
      >
        🔍
      </span>

      <input
        type="search"
        value={localValue}
        onChange={handleChange}
        placeholder={placeholder}
        aria-label="Search tasks"
        style={{
          width: "100%",
          padding: "8px 36px 8px 36px",
          backgroundColor: "var(--color-surface)",
          color: "var(--color-text-primary)",
          border: "1px solid var(--color-border)",
          borderRadius: "8px",
          fontFamily: "'Inter', sans-serif",
          fontSize: "14px",
          outline: "none",
          transition: "border-color 150ms ease",
          // Remove browser default search input clear button — we render our own
          WebkitAppearance: "none",
        }}
        onFocus={(e) =>
          (e.target.style.borderColor = "var(--color-cta-primary)")
        }
        onBlur={(e) =>
          (e.target.style.borderColor = "var(--color-border)")
        }
      />

      {/* Clear button — only rendered when the input has content */}
      {localValue && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search"
          style={{
            position: "absolute",
            right: "10px",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--color-text-secondary)",
            fontSize: "16px",
            lineHeight: 1,
            padding: "2px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
