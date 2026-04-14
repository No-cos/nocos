// page.tsx (Landing page — /)
// Entry point for the Nocos discovery platform.
// Phase 1: Placeholder shell. Full implementation in Phase 3.
// TODO: Replace placeholder with full discovery grid — see Phase 3

export default function HomePage() {
  return (
    <main
      style={{
        backgroundColor: "var(--color-bg)",
        color: "var(--color-text-primary)",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: "600px", padding: "2rem" }}>
        <h1
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: "2.5rem",
            fontWeight: 800,
            color: "var(--color-cta-primary)",
            marginBottom: "1rem",
          }}
        >
          Nocos
        </h1>
        <p
          style={{
            fontSize: "1.125rem",
            color: "var(--color-text-secondary)",
            marginBottom: "2rem",
          }}
        >
          Discover and Contribute to Your Favourite Open Source Project.
        </p>
        <p
          style={{
            fontSize: "0.875rem",
            color: "var(--color-text-secondary)",
          }}
        >
          Phase 1 foundation is live. Full UI coming in Phase 3.
        </p>
      </div>
    </main>
  );
}
