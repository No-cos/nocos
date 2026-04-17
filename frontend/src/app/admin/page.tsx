"use client";

/**
 * Admin moderation page — /admin
 *
 * Private, standalone page (no public Navbar). Not linked from any public-
 * facing navigation. Authentication is entirely client-side via a token
 * stored in localStorage — never server-rendered with sensitive data.
 *
 * Flow:
 *  1. On mount, check localStorage for "admin_token".
 *  2. If found, verify by calling GET /api/v1/admin/pending.
 *     - 200  → show dashboard.
 *     - 401/403/other → clear token, show login form.
 *  3. Login form: enter token → test → save or show error.
 *  4. Dashboard: list pending tasks with Approve / Reject buttons.
 *     Reject opens an inline reason picker before confirming.
 *     Each action removes the card with a fade-out and shows a toast.
 */

import { useState, useEffect, useCallback } from "react";
import { Trash2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STORAGE_KEY = "admin_token";

const REJECTION_REASONS = [
  "Does not meet open source requirements",
  "Not a non-code contribution",
  "Duplicate issue already listed",
  "Insufficient information provided",
  "Project is not actively maintained",
  "Other",
] as const;

// ── Types ─────────────────────────────────────────────────────────────────────

interface PendingTask {
  id: string;
  title: string;
  contribution_type: string;
  is_paid: boolean;
  difficulty: string | null;
  source: string;
  github_issue_url: string;
  description_display: string;
  submitter_email: string | null;
  created_at: string;
  project: {
    id: string;
    name: string;
    github_owner: string;
    github_repo: string;
  };
}

interface ModerationStats {
  pending_review: number;
  approved: number;
  rejected: number;
  total_subscribers: number;
}

interface AllTask {
  id: string;
  title: string;
  contribution_type: string;
  review_status: string;
  is_active: boolean;
  source: string;
  created_at: string;
  project: {
    github_owner: string;
    github_repo: string;
  };
}

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

// ── Admin fetch helper ────────────────────────────────────────────────────────

async function adminFetch<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(
      new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`),
      { status: res.status }
    );
  }
  return res.json() as Promise<T>;
}

// ── Page component ────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [token, setToken] = useState<string>("");
  const [tokenInput, setTokenInput] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [tasks, setTasks] = useState<PendingTask[]>([]);
  const [stats, setStats] = useState<ModerationStats | null>(null);
  const [loading, setLoading] = useState(false);

  // All-tasks management table
  const [allTasks, setAllTasks] = useState<AllTask[]>([]);
  const [allTasksLoading, setAllTasksLoading] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  // Cards being removed via fade-out animation
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());

  // Inline rejection panel state — only one card open at a time
  const [rejectingTaskId, setRejectingTaskId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<string>(REJECTION_REASONS[0]);

  // Toast notifications
  const [toasts, setToasts] = useState<Toast[]>([]);

  // ── Toast helpers ───────────────────────────────────────────────────────────

  function showToast(message: string, type: "success" | "error") {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }

  // ── Data loading ────────────────────────────────────────────────────────────

  const loadDashboard = useCallback(async (t: string) => {
    setLoading(true);
    setAllTasksLoading(true);
    try {
      const [pendingRes, statsRes, allRes] = await Promise.all([
        adminFetch<{ success: boolean; count: number; data: PendingTask[] }>(
          "/api/v1/admin/pending",
          t
        ),
        adminFetch<{ success: boolean } & ModerationStats>(
          "/api/v1/admin/stats",
          t
        ),
        adminFetch<{ success: boolean; count: number; data: AllTask[] }>(
          "/api/v1/admin/tasks",
          t
        ),
      ]);
      setTasks(pendingRes.data);
      setStats({
        pending_review: statsRes.pending_review,
        approved: statsRes.approved,
        rejected: statsRes.rejected,
        total_subscribers: statsRes.total_subscribers ?? 0,
      });
      setAllTasks(allRes.data);
    } catch {
      showToast("Failed to load data. Check your connection.", "error");
    } finally {
      setLoading(false);
      setAllTasksLoading(false);
    }
  }, []);

  // ── Token verification ──────────────────────────────────────────────────────

  const verifyAndLogin = useCallback(
    async (t: string) => {
      setIsVerifying(true);
      setLoginError(null);
      try {
        await adminFetch("/api/v1/admin/pending", t);
        localStorage.setItem(STORAGE_KEY, t);
        setToken(t);
        setIsLoggedIn(true);
        await loadDashboard(t);
      } catch (err) {
        const status = (err as { status?: number }).status;
        if (status === 401 || status === 403) {
          setLoginError("Invalid token. Please try again.");
        } else {
          setLoginError("Could not reach the server. Check your connection.");
        }
        localStorage.removeItem(STORAGE_KEY);
      } finally {
        setIsVerifying(false);
      }
    },
    [loadDashboard]
  );

  // ── On mount: restore saved token ──────────────────────────────────────────

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      verifyAndLogin(saved);
    }
  }, [verifyAndLogin]);

  // ── Sign out ────────────────────────────────────────────────────────────────

  function signOut() {
    localStorage.removeItem(STORAGE_KEY);
    setToken("");
    setIsLoggedIn(false);
    setTasks([]);
    setStats(null);
    setTokenInput("");
    setLoginError(null);
    setRejectingTaskId(null);
  }

  // ── Shared removal helper ───────────────────────────────────────────────────

  function animateRemove(
    taskId: string,
    action: "approve" | "reject"
  ) {
    setRemovingIds((prev) => new Set(prev).add(taskId));
    setTimeout(() => {
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setRemovingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
      setStats((prev) =>
        prev
          ? {
              ...prev,
              pending_review: Math.max(0, prev.pending_review - 1),
              approved: action === "approve" ? prev.approved + 1 : prev.approved,
              rejected: action === "reject" ? prev.rejected + 1 : prev.rejected,
            }
          : prev
      );
    }, 350);
  }

  // ── Approve ─────────────────────────────────────────────────────────────────

  async function handleApprove(taskId: string) {
    setRemovingIds((prev) => new Set(prev).add(taskId));
    try {
      await adminFetch(`/api/v1/admin/approve/${taskId}`, token, {
        method: "POST",
      });
      animateRemove(taskId, "approve");
      showToast("Task approved", "success");
    } catch {
      setRemovingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
      showToast("Action failed. Please try again.", "error");
    }
  }

  // ── Reject with reason ──────────────────────────────────────────────────────

  async function handleConfirmReject(taskId: string) {
    setRejectingTaskId(null);
    setRemovingIds((prev) => new Set(prev).add(taskId));
    try {
      await adminFetch(`/api/v1/admin/reject/${taskId}`, token, {
        method: "POST",
        body: JSON.stringify({ reason: rejectReason }),
      });
      animateRemove(taskId, "reject");
      showToast("Task rejected", "success");
    } catch {
      setRemovingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
      showToast("Action failed. Please try again.", "error");
    }
  }

  function openRejectPanel(taskId: string) {
    setRejectReason(REJECTION_REASONS[0]);
    setRejectingTaskId(taskId);
  }

  // ── Delete task (management table) ─────────────────────────────────────────

  async function handleDeleteTask(taskId: string) {
    setConfirmDeleteId(null);
    setDeletingIds((prev) => new Set(prev).add(taskId));
    try {
      await adminFetch(`/api/v1/admin/tasks/${taskId}`, token, {
        method: "DELETE",
      });
      setAllTasks((prev) => prev.filter((t) => t.id !== taskId));
      showToast("Task deleted", "success");
    } catch {
      showToast("Delete failed. Please try again.", "error");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  }

  // ── Login form ──────────────────────────────────────────────────────────────

  if (!isLoggedIn) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "var(--color-bg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "380px",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "12px",
            padding: "40px 32px",
          }}
        >
          <h1
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "1.5rem",
              color: "var(--color-text-primary)",
              margin: "0 0 8px",
            }}
          >
            Admin
          </h1>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.875rem",
              color: "var(--color-text-secondary)",
              margin: "0 0 28px",
            }}
          >
            Enter your admin token to continue.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (tokenInput.trim()) verifyAndLogin(tokenInput.trim());
            }}
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => {
                setTokenInput(e.target.value);
                setLoginError(null);
              }}
              placeholder="Admin token"
              autoComplete="current-password"
              style={{
                display: "block",
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                fontFamily: "'Inter', sans-serif",
                fontSize: "0.9375rem",
                color: "var(--color-text-primary)",
                backgroundColor: "var(--color-bg)",
                border: `1px solid ${loginError ? "var(--color-status-inactive)" : "var(--color-border)"}`,
                borderRadius: "8px",
                outline: "none",
              }}
            />

            {loginError && (
              <p
                role="alert"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "12px",
                  color: "var(--color-status-inactive)",
                  margin: 0,
                }}
              >
                {loginError}
              </p>
            )}

            <button
              type="submit"
              disabled={isVerifying || !tokenInput.trim()}
              style={{
                padding: "10px 20px",
                backgroundColor:
                  isVerifying || !tokenInput.trim()
                    ? "var(--color-border)"
                    : "var(--color-cta-primary)",
                color:
                  isVerifying || !tokenInput.trim()
                    ? "var(--color-text-secondary)"
                    : "#ffffff",
                fontFamily: "'Inter', sans-serif",
                fontWeight: 600,
                fontSize: "0.9375rem",
                borderRadius: "8px",
                border: "none",
                cursor:
                  isVerifying || !tokenInput.trim() ? "not-allowed" : "pointer",
                transition: "background-color 150ms ease",
              }}
            >
              {isVerifying ? "Verifying…" : "Enter"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Dashboard ───────────────────────────────────────────────────────────────

  const pendingCount = stats?.pending_review ?? tasks.length;

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--color-bg)",
        padding: "0 0 80px",
      }}
    >
      {/* Toast container */}
      <div
        aria-live="polite"
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 200,
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            style={{
              padding: "12px 20px",
              borderRadius: "8px",
              backgroundColor:
                toast.type === "success"
                  ? "var(--color-status-active)"
                  : "var(--color-status-inactive)",
              color: "#ffffff",
              fontFamily: "'Inter', sans-serif",
              fontWeight: 500,
              fontSize: "0.875rem",
              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            }}
          >
            {toast.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <div
        style={{
          backgroundColor: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border)",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            maxWidth: "960px",
            margin: "0 auto",
            height: "64px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h1
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "1.125rem",
              color: "var(--color-text-primary)",
              margin: 0,
            }}
          >
            Pending Review ({pendingCount})
          </h1>
          <button
            onClick={signOut}
            style={{
              padding: "7px 16px",
              backgroundColor: "transparent",
              color: "var(--color-text-secondary)",
              fontFamily: "'Inter', sans-serif",
              fontWeight: 500,
              fontSize: "0.875rem",
              borderRadius: "8px",
              border: "1px solid var(--color-border)",
              cursor: "pointer",
              transition: "border-color 150ms ease, color 150ms ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.color =
                "var(--color-text-primary)";
              (e.currentTarget as HTMLElement).style.borderColor =
                "var(--color-text-secondary)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.color =
                "var(--color-text-secondary)";
              (e.currentTarget as HTMLElement).style.borderColor =
                "var(--color-border)";
            }}
          >
            Sign out
          </button>
        </div>
      </div>

      <div
        style={{
          maxWidth: "960px",
          margin: "0 auto",
          padding: "32px 24px 0",
        }}
      >
        {/* Stats row */}
        {stats && (
          <div
            style={{
              display: "flex",
              gap: "16px",
              marginBottom: "32px",
              flexWrap: "wrap",
            }}
          >
            {(
              [
                {
                  label: "Pending",
                  value: stats.pending_review,
                  color: "var(--color-status-slow)",
                },
                {
                  label: "Approved",
                  value: stats.approved,
                  color: "var(--color-status-active)",
                },
                {
                  label: "Rejected",
                  value: stats.rejected,
                  color: "var(--color-status-inactive)",
                },
                {
                  label: "Subscribers",
                  value: stats.total_subscribers,
                  color: "var(--color-cta-primary)",
                },
              ] as const
            ).map(({ label, value, color }) => (
              <div
                key={label}
                style={{
                  flex: "1 1 140px",
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "10px",
                  padding: "16px 20px",
                }}
              >
                <div
                  style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    fontWeight: 700,
                    fontSize: "1.75rem",
                    color,
                    lineHeight: 1,
                    marginBottom: "4px",
                  }}
                >
                  {value}
                </div>
                <div
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "0.8125rem",
                    color: "var(--color-text-secondary)",
                  }}
                >
                  {label}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div
            style={{
              textAlign: "center",
              padding: "60px 0",
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--color-text-secondary)",
            }}
          >
            Loading…
          </div>
        )}

        {/* Empty state */}
        {!loading && tasks.length === 0 && (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div
              aria-hidden="true"
              style={{ fontSize: "2.5rem", marginBottom: "16px" }}
            >
              ✅
            </div>
            <p
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700,
                fontSize: "1.25rem",
                color: "var(--color-text-primary)",
                margin: "0 0 8px",
              }}
            >
              All caught up
            </p>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "0.9375rem",
                color: "var(--color-text-secondary)",
                margin: 0,
              }}
            >
              No tasks pending review.
            </p>
          </div>
        )}

        {/* ── Pending task cards ─────────────────────────────────────── */}
        {!loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {tasks.map((task) => {
              const isRemoving = removingIds.has(task.id);
              const isRejectOpen = rejectingTaskId === task.id;

              return (
                <div
                  key={task.id}
                  style={{
                    backgroundColor: "var(--color-surface)",
                    border: `1px solid ${isRejectOpen ? "var(--color-status-inactive)" : "var(--color-border)"}`,
                    borderRadius: "12px",
                    padding: "20px 24px",
                    opacity: isRemoving ? 0 : 1,
                    transform: isRemoving
                      ? "translateY(-6px)"
                      : "translateY(0)",
                    transition:
                      "opacity 350ms ease, transform 350ms ease, border-color 150ms ease",
                  }}
                >
                  {/* Card header: title + type tag */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      marginBottom: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    <h2
                      style={{
                        fontFamily: "'Plus Jakarta Sans', sans-serif",
                        fontWeight: 600,
                        fontSize: "1rem",
                        color: "var(--color-text-primary)",
                        margin: 0,
                        flex: 1,
                        minWidth: "200px",
                      }}
                    >
                      {task.title}
                    </h2>
                    <span
                      style={{
                        backgroundColor: "var(--color-bg)",
                        border: "1.5px solid var(--color-border)",
                        borderRadius: "999px",
                        fontFamily: "'Inter', sans-serif",
                        fontSize: "12px",
                        fontWeight: 500,
                        padding: "3px 10px",
                        color: "var(--color-text-secondary)",
                        whiteSpace: "nowrap",
                        flexShrink: 0,
                      }}
                    >
                      {task.contribution_type.replace(/_/g, " ")}
                    </span>
                  </div>

                  {/* Meta row */}
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "12px",
                      marginBottom: "12px",
                    }}
                  >
                    <MetaChip label="Project" value={task.project.name} />
                    <MetaChip
                      label="Source"
                      value={
                        task.source === "manual_post" ? "Manual post" : "GitHub"
                      }
                    />
                    {task.submitter_email && (
                      <MetaChip label="Email" value={task.submitter_email} />
                    )}
                    <MetaChip
                      label="Submitted"
                      value={new Date(task.created_at).toLocaleString(
                        undefined,
                        { dateStyle: "medium", timeStyle: "short" }
                      )}
                    />
                  </div>

                  {/* Description excerpt */}
                  <p
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: "0.875rem",
                      color: "var(--color-text-secondary)",
                      lineHeight: 1.6,
                      margin: "0 0 16px",
                    }}
                  >
                    {task.description_display.length > 200
                      ? task.description_display.slice(0, 200) + "…"
                      : task.description_display}
                  </p>

                  {/* ── Actions ───────────────────────────────────────────── */}
                  {!isRejectOpen ? (
                    /* Default: Approve + Reject buttons */
                    <div style={{ display: "flex", gap: "10px" }}>
                      <button
                        onClick={() => handleApprove(task.id)}
                        disabled={isRemoving}
                        style={actionBtnStyle(
                          "var(--color-status-active)",
                          isRemoving
                        )}
                        onMouseEnter={(e) => {
                          if (!isRemoving)
                            (e.currentTarget as HTMLElement).style.opacity =
                              "0.85";
                        }}
                        onMouseLeave={(e) => {
                          if (!isRemoving)
                            (e.currentTarget as HTMLElement).style.opacity =
                              "1";
                        }}
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => openRejectPanel(task.id)}
                        disabled={isRemoving}
                        style={actionBtnStyle(
                          "var(--color-status-inactive)",
                          isRemoving
                        )}
                        onMouseEnter={(e) => {
                          if (!isRemoving)
                            (e.currentTarget as HTMLElement).style.opacity =
                              "0.85";
                        }}
                        onMouseLeave={(e) => {
                          if (!isRemoving)
                            (e.currentTarget as HTMLElement).style.opacity =
                              "1";
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    /* Rejection panel: reason selector + confirm / cancel */
                    <div
                      style={{
                        borderTop: "1px solid var(--color-border)",
                        paddingTop: "16px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px",
                      }}
                    >
                      <label
                        htmlFor={`reject-reason-${task.id}`}
                        style={{
                          fontFamily: "'Inter', sans-serif",
                          fontWeight: 600,
                          fontSize: "0.8125rem",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        Rejection reason
                      </label>
                      <select
                        id={`reject-reason-${task.id}`}
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        style={{
                          display: "block",
                          width: "100%",
                          padding: "9px 12px",
                          fontFamily: "'Inter', sans-serif",
                          fontSize: "0.875rem",
                          color: "var(--color-text-primary)",
                          backgroundColor: "var(--color-bg)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "8px",
                          outline: "none",
                          cursor: "pointer",
                        }}
                      >
                        {REJECTION_REASONS.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>

                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "16px",
                        }}
                      >
                        <button
                          onClick={() => handleConfirmReject(task.id)}
                          style={actionBtnStyle(
                            "var(--color-status-inactive)",
                            false
                          )}
                          onMouseEnter={(e) => {
                            (e.currentTarget as HTMLElement).style.opacity =
                              "0.85";
                          }}
                          onMouseLeave={(e) => {
                            (e.currentTarget as HTMLElement).style.opacity =
                              "1";
                          }}
                        >
                          Confirm Rejection
                        </button>
                        <button
                          onClick={() => setRejectingTaskId(null)}
                          style={{
                            background: "none",
                            border: "none",
                            fontFamily: "'Inter', sans-serif",
                            fontSize: "0.875rem",
                            color: "var(--color-text-secondary)",
                            cursor: "pointer",
                            padding: "0",
                            textDecoration: "underline",
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {/* ── All Tasks management table ─────────────────────────────── */}
        <div style={{ marginTop: "56px" }}>
          <h2
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "1.125rem",
              color: "var(--color-text-primary)",
              margin: "0 0 20px",
            }}
          >
            All Tasks ({allTasks.length})
          </h2>

          {allTasksLoading && (
            <div
              style={{
                textAlign: "center",
                padding: "40px 0",
                fontFamily: "'Inter', sans-serif",
                fontSize: "0.9375rem",
                color: "var(--color-text-secondary)",
              }}
            >
              Loading…
            </div>
          )}

          {!allTasksLoading && allTasks.length === 0 && (
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "0.9375rem",
                color: "var(--color-text-secondary)",
                padding: "32px 0",
                textAlign: "center",
              }}
            >
              No tasks in the database.
            </p>
          )}

          {!allTasksLoading && allTasks.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "0.8125rem",
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid var(--color-border)",
                      textAlign: "left",
                    }}
                  >
                    {(["Repo", "Title", "Category", "Status", "Date added", ""] as const).map(
                      (col) => (
                        <th
                          key={col}
                          style={{
                            padding: "10px 12px",
                            fontWeight: 600,
                            color: "var(--color-text-secondary)",
                            whiteSpace: "nowrap",
                          }}
                          className={
                            col === "Category" || col === "Status" || col === "Date added"
                              ? "admin-col-hide-mobile"
                              : undefined
                          }
                        >
                          {col}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {allTasks.map((task) => {
                    const isDeleting = deletingIds.has(task.id);
                    const isConfirming = confirmDeleteId === task.id;
                    const repo = `${task.project.github_owner}/${task.project.github_repo}`;
                    const title =
                      task.title.length > 60
                        ? task.title.slice(0, 60) + "…"
                        : task.title;

                    return (
                      <tr
                        key={task.id}
                        style={{
                          borderBottom: "1px solid var(--color-border)",
                          opacity: isDeleting ? 0.4 : 1,
                          transition: "opacity 200ms ease",
                          backgroundColor: isConfirming
                            ? "color-mix(in srgb, var(--color-status-inactive) 6%, transparent)"
                            : "transparent",
                        }}
                      >
                        {/* Repo */}
                        <td
                          style={{
                            padding: "12px 12px",
                            color: "var(--color-text-secondary)",
                            whiteSpace: "nowrap",
                            maxWidth: "160px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {repo}
                        </td>

                        {/* Title */}
                        <td
                          style={{
                            padding: "12px 12px",
                            color: "var(--color-text-primary)",
                            maxWidth: "280px",
                          }}
                        >
                          {title}
                        </td>

                        {/* Category — hidden on mobile */}
                        <td
                          className="admin-col-hide-mobile"
                          style={{
                            padding: "12px 12px",
                            color: "var(--color-text-secondary)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {task.contribution_type.replace(/_/g, " ")}
                        </td>

                        {/* Status — hidden on mobile */}
                        <td
                          className="admin-col-hide-mobile"
                          style={{ padding: "12px 12px", whiteSpace: "nowrap" }}
                        >
                          <span
                            style={{
                              display: "inline-block",
                              padding: "2px 8px",
                              borderRadius: "999px",
                              fontSize: "11px",
                              fontWeight: 600,
                              backgroundColor:
                                task.review_status === "approved"
                                  ? "color-mix(in srgb, var(--color-status-active) 15%, transparent)"
                                  : task.review_status === "rejected"
                                  ? "color-mix(in srgb, var(--color-status-inactive) 15%, transparent)"
                                  : "color-mix(in srgb, var(--color-status-slow) 15%, transparent)",
                              color:
                                task.review_status === "approved"
                                  ? "var(--color-status-active)"
                                  : task.review_status === "rejected"
                                  ? "var(--color-status-inactive)"
                                  : "var(--color-status-slow)",
                            }}
                          >
                            {task.review_status === "pending_review"
                              ? "pending"
                              : task.review_status}
                          </span>
                        </td>

                        {/* Date — hidden on mobile */}
                        <td
                          className="admin-col-hide-mobile"
                          style={{
                            padding: "12px 12px",
                            color: "var(--color-text-secondary)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {new Date(task.created_at).toLocaleDateString(
                            undefined,
                            { dateStyle: "medium" }
                          )}
                        </td>

                        {/* Delete */}
                        <td
                          style={{
                            padding: "12px 12px",
                            textAlign: "right",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {isConfirming ? (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "8px",
                              }}
                            >
                              <button
                                onClick={() => handleDeleteTask(task.id)}
                                disabled={isDeleting}
                                style={deleteBtnStyle(true)}
                              >
                                Confirm
                              </button>
                              <button
                                onClick={() => setConfirmDeleteId(null)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  fontFamily: "'Inter', sans-serif",
                                  fontSize: "0.8125rem",
                                  color: "var(--color-text-secondary)",
                                  cursor: "pointer",
                                  padding: 0,
                                  textDecoration: "underline",
                                }}
                              >
                                Cancel
                              </button>
                            </span>
                          ) : (
                            <button
                              onClick={() => setConfirmDeleteId(task.id)}
                              disabled={isDeleting}
                              aria-label={`Delete task: ${task.title}`}
                              style={deleteBtnStyle(false)}
                              onMouseEnter={(e) => {
                                if (!isDeleting)
                                  (e.currentTarget as HTMLElement).style.opacity = "0.8";
                              }}
                              onMouseLeave={(e) => {
                                if (!isDeleting)
                                  (e.currentTarget as HTMLElement).style.opacity = "1";
                              }}
                            >
                              <Trash2 size={14} strokeWidth={1.5} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── MetaChip ──────────────────────────────────────────────────────────────────

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <span
      style={{
        fontFamily: "'Inter', sans-serif",
        fontSize: "12px",
        color: "var(--color-text-secondary)",
      }}
    >
      <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
        {label}:{" "}
      </span>
      {value}
    </span>
  );
}

// ── deleteBtnStyle ────────────────────────────────────────────────────────────

function deleteBtnStyle(confirm: boolean): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: confirm ? "5px 12px" : "5px 8px",
    backgroundColor: confirm
      ? "var(--color-status-inactive)"
      : "color-mix(in srgb, var(--color-status-inactive) 12%, transparent)",
    color: confirm ? "#ffffff" : "var(--color-status-inactive)",
    border: `1px solid ${confirm ? "var(--color-status-inactive)" : "color-mix(in srgb, var(--color-status-inactive) 30%, transparent)"}`,
    borderRadius: "6px",
    fontFamily: "'Inter', sans-serif",
    fontWeight: 600,
    fontSize: "0.8125rem",
    cursor: "pointer",
    transition: "opacity 150ms ease",
    gap: "4px",
  };
}

// ── actionBtnStyle ────────────────────────────────────────────────────────────

function actionBtnStyle(
  bgColor: string,
  disabled: boolean
): React.CSSProperties {
  return {
    padding: "8px 20px",
    backgroundColor: bgColor,
    color: "#ffffff",
    fontFamily: "'Inter', sans-serif",
    fontWeight: 600,
    fontSize: "0.875rem",
    borderRadius: "8px",
    border: "none",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    transition: "opacity 150ms ease",
  };
}
