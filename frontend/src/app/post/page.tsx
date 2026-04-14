// page.tsx (Post a Task — /post)
// Form for maintainers to manually list a non-code task on Nocos.
// Phase 1: Placeholder shell. Full implementation in Phase 5.
// TODO: Build full form with validation and live preview — see Phase 5

export default function PostTaskPage() {
  return (
    <main
      style={{
        backgroundColor: "var(--color-bg)",
        color: "var(--color-text-primary)",
        minHeight: "100vh",
        padding: "2rem",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div
        style={{
          maxWidth: "var(--detail-max-width)",
          margin: "0 auto",
        }}
      >
        <h1
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: "1.5rem",
            fontWeight: 700,
          }}
        >
          Post a Task
        </h1>
        <p style={{ color: "var(--color-text-secondary)", marginTop: "1rem" }}>
          Maintainer task submission form coming in Phase 5.
        </p>
      </div>
    </main>
  );
}
