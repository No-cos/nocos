/**
 * IssueCardSkeleton — loading placeholder for an IssueCard.
 *
 * Uses a shimmer animation matching the card's structure so the layout
 * stays stable while data loads. Preferred over a spinner because it
 * communicates what content is coming (SKILLS.md §6).
 */

export function IssueCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      {/* Avatar + name row */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div className="skeleton-pulse" style={{ width: 32, height: 32, borderRadius: "50%" }} />
        <div className="skeleton-pulse" style={{ width: "40%", height: 12, borderRadius: 6 }} />
      </div>
      {/* Title */}
      <div className="skeleton-pulse" style={{ width: "90%", height: 16, borderRadius: 6 }} />
      <div className="skeleton-pulse" style={{ width: "60%", height: 16, borderRadius: 6 }} />
      {/* Tags */}
      <div style={{ display: "flex", gap: 6 }}>
        {[60, 80, 70].map((w, i) => (
          <div key={i} className="skeleton-pulse" style={{ width: w, height: 22, borderRadius: 999 }} />
        ))}
      </div>
      {/* Description lines */}
      {[100, 95, 80].map((pct, i) => (
        <div key={i} className="skeleton-pulse" style={{ width: `${pct}%`, height: 12, borderRadius: 6 }} />
      ))}
      {/* Bottom row */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
        <div className="skeleton-pulse" style={{ width: 60, height: 12, borderRadius: 6 }} />
      </div>

      <style>{`
        .skeleton-pulse {
          background: linear-gradient(
            90deg,
            var(--color-border) 25%,
            var(--color-surface) 50%,
            var(--color-border) 75%
          );
          background-size: 200% 100%;
          animation: skeleton-shimmer 1.4s ease infinite;
        }
        @keyframes skeleton-shimmer {
          0%   { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}
