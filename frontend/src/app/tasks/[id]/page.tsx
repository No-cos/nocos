// page.tsx (Task detail page — /tasks/[id])
// Displays full details for a single non-code issue.
// Phase 1: Placeholder shell. Full implementation in Phase 4.
// TODO: Fetch task by ID from /api/v1/issues/:id — see Phase 4

interface TaskDetailPageProps {
  params: { id: string };
}

export default function TaskDetailPage({ params }: TaskDetailPageProps) {
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
          Task {params.id}
        </h1>
        <p style={{ color: "var(--color-text-secondary)", marginTop: "1rem" }}>
          Full task detail page coming in Phase 4.
        </p>
      </div>
    </main>
  );
}
