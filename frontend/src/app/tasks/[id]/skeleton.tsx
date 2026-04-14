/**
 * DetailPageSkeleton — loading placeholder for the task detail page.
 *
 * Mirrors the structure of the real page so the layout is stable
 * while the API call resolves. Preferred over a spinner (SKILLS.md §6).
 */

export function DetailPageSkeleton() {
  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "40px 24px 120px" }}>
      {/* Title */}
      <div className="sk" style={{ width: "80%", height: 32, borderRadius: 8, marginBottom: 20 }} />
      <div className="sk" style={{ width: "55%", height: 32, borderRadius: 8, marginBottom: 28 }} />

      {/* Tags */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {[80, 100, 70].map((w, i) => (
          <div key={i} className="sk" style={{ width: w, height: 24, borderRadius: 999 }} />
        ))}
      </div>

      {/* Description lines */}
      {[100, 98, 95, 88, 60].map((pct, i) => (
        <div key={i} className="sk" style={{ width: `${pct}%`, height: 14, borderRadius: 6, marginBottom: 10 }} />
      ))}

      {/* GitHub URL row */}
      <div className="sk" style={{ width: "50%", height: 14, borderRadius: 6, marginTop: 24, marginBottom: 32 }} />

      {/* Divider */}
      <div style={{ height: 1, backgroundColor: "var(--color-border)", marginBottom: 32 }} />

      {/* About section label */}
      <div className="sk" style={{ width: 120, height: 11, borderRadius: 6, marginBottom: 20 }} />

      {/* Avatar + project name */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div className="sk" style={{ width: 40, height: 40, borderRadius: "50%", flexShrink: 0 }} />
        <div className="sk" style={{ width: 180, height: 20, borderRadius: 6 }} />
      </div>

      {/* Project description */}
      {[100, 92, 70].map((pct, i) => (
        <div key={i} className="sk" style={{ width: `${pct}%`, height: 13, borderRadius: 6, marginBottom: 8 }} />
      ))}

    </div>
  );
}
