/**
 * Pagination component — page controls for the issue discovery grid.
 *
 * Renders: Prev [1] [2] [3] [...] [22] [23] [24] Next + View All button.
 * Shows at most 7 page buttons, using ellipsis to collapse the middle range.
 *
 * @param currentPage - 1-indexed current page
 * @param totalPages  - Total number of pages
 * @param onPageChange - Called with the new page number
 */

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  // Build the list of page items to render, inserting "..." where needed.
  // We always show the first, last, current, and two neighbours.
  function getPages(): (number | "...")[] {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages: (number | "...")[] = [1];
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);

    if (start > 2) pages.push("...");
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push("...");
    pages.push(totalPages);
    return pages;
  }

  const btnStyle = (active: boolean, disabled?: boolean): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "36px",
    height: "36px",
    padding: "0 8px",
    borderRadius: "8px",
    border: active
      ? "1.5px solid var(--color-cta-primary)"
      : "1px solid var(--color-border)",
    backgroundColor: active ? "var(--color-cta-primary)" : "var(--color-surface)",
    color: active ? "#ffffff" : disabled ? "var(--color-border)" : "var(--color-text-primary)",
    fontFamily: "'Inter', sans-serif",
    fontSize: "13px",
    fontWeight: active ? 600 : 400,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: "border-color 150ms ease, background 150ms ease",
    opacity: disabled ? 0.5 : 1,
  });

  return (
    <nav aria-label="Issue list pagination" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
      <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
        {/* Prev */}
        <button
          style={btnStyle(false, currentPage === 1)}
          onClick={() => currentPage > 1 && onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label="Previous page"
        >
          ← Prev
        </button>

        {/* Page numbers */}
        {getPages().map((item, i) =>
          item === "..." ? (
            <span key={`ellipsis-${i}`} style={{ padding: "0 4px", color: "var(--color-text-secondary)", fontSize: "13px" }}>
              …
            </span>
          ) : (
            <button
              key={item}
              style={btnStyle(item === currentPage)}
              onClick={() => onPageChange(item as number)}
              aria-label={`Page ${item}`}
              aria-current={item === currentPage ? "page" : undefined}
            >
              {item}
            </button>
          )
        )}

        {/* Next */}
        <button
          style={btnStyle(false, currentPage === totalPages)}
          onClick={() => currentPage < totalPages && onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          aria-label="Next page"
        >
          Next →
        </button>
      </div>

      {/* View All */}
      <a
        href="/?page=1&limit=50"
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "13px",
          fontWeight: 500,
          color: "var(--color-cta-primary)",
          textDecoration: "none",
          padding: "8px 16px",
          border: "1px solid var(--color-cta-primary)",
          borderRadius: "8px",
          transition: "background 150ms ease",
        }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor =
            "color-mix(in srgb, var(--color-cta-primary) 8%, transparent)")
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor = "transparent")
        }
      >
        View All
      </a>
    </nav>
  );
}
