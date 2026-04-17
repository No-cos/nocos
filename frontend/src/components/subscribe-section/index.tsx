"use client";

/**
 * SubscribeSection component — email digest signup above the footer.
 *
 * Flow:
 * 1. User enters email → "Subscribe →" button submits to POST /api/v1/subscribe
 * 2. On success: form replaced with confirmation message
 * 3. On error / invalid email: inline validation message shown
 * 4. After email entry: optional tag preference multi-select appears
 *
 * Layout: email input + button inline on desktop, stacked on mobile.
 * All colours via CSS variables — no hardcoded hex.
 */

import { useState } from "react";
import { Tag, ALL_CONTRIBUTION_TYPES } from "@/components/ui/tag";
import { subscribeEmail } from "@/lib/api";
import { isValidEmail, formatContributionType } from "@/lib/utils";
import { useInView } from "@/hooks/use-in-view";

type State = "idle" | "loading" | "success" | "error";

export function SubscribeSection() {
  const [email, setEmail] = useState("");
  const [tagPrefs, setTagPrefs] = useState<string[]>([]);
  const [showTagPrefs, setShowTagPrefs] = useState(false);
  const [state, setState] = useState<State>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const { ref, inView } = useInView<HTMLElement>();

  function toggleTag(type: string) {
    setTagPrefs((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg("");

    if (!isValidEmail(email)) {
      setErrorMsg("Please enter a valid email address.");
      return;
    }

    setState("loading");
    // Show tag preference selector while the request is in-flight
    setShowTagPrefs(true);

    try {
      await subscribeEmail(email, tagPrefs);
      setState("success");
    } catch {
      setState("error");
      setErrorMsg(
        "Something went wrong. Please try again."
      );
    }
  }

  return (
    /* Outer section: no background, just vertical breathing room + horizontal gutter */
    <section
      ref={ref}
      className={`reveal${inView ? " visible" : ""}`}
      style={{
        padding: "64px 24px",
      }}
      aria-labelledby="subscribe-headline"
    >
      {/* Constrained pill — background, border, and rounded corners live here */}
      <div
        style={{
          maxWidth: "var(--content-max-width)",
          margin: "0 auto",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "20px",
          padding: "64px 24px",
          textAlign: "center",
        }}
      >
      <div style={{ maxWidth: "560px", margin: "0 auto" }}>
        <h2
          id="subscribe-headline"
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(1.5rem, 4vw, 2rem)",
            color: "var(--color-text-primary)",
            margin: "0 0 12px",
          }}
        >
          Stay in the loop.
        </h2>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "1rem",
            color: "var(--color-text-secondary)",
            lineHeight: 1.6,
            margin: "0 0 32px",
          }}
        >
          Get curated non-code issues delivered to your inbox weekly. No spam.
        </p>

        {/* ── Success state ────────────────────────────────────────────── */}
        {state === "success" ? (
          <p
            role="status"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 500,
              fontSize: "1rem",
              color: "var(--color-text-primary)",
              padding: "20px",
              border: "1px solid var(--color-border)",
              borderRadius: "12px",
              backgroundColor: "var(--color-bg)",
            }}
          >
            ✅ You're on the list. Check your inbox for a confirmation.
          </p>
        ) : (
          /* ── Form ──────────────────────────────────────────────────── */
          <form onSubmit={handleSubmit} noValidate>
            <div className="subscribe-input-row">
              <input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setShowTagPrefs(e.target.value.length > 4);
                }}
                placeholder="you@example.com"
                aria-label="Email address"
                aria-describedby={errorMsg ? "subscribe-error" : undefined}
                aria-invalid={!!errorMsg}
                required
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  backgroundColor: "var(--color-bg)",
                  color: "var(--color-text-primary)",
                  border: `1px solid ${errorMsg ? "#EF4444" : "var(--color-border)"}`,
                  borderRadius: "10px",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "0.9375rem",
                  outline: "none",
                  transition: "border-color 150ms ease",
                  minWidth: 0,
                }}
                onFocus={(e) => {
                  if (!errorMsg)
                    e.target.style.borderColor = "var(--color-cta-primary)";
                }}
                onBlur={(e) => {
                  if (!errorMsg)
                    e.target.style.borderColor = "var(--color-border)";
                }}
              />

              <button
                type="submit"
                disabled={state === "loading"}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "var(--color-cta-primary)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "10px",
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600,
                  fontSize: "0.9375rem",
                  cursor: state === "loading" ? "not-allowed" : "pointer",
                  opacity: state === "loading" ? 0.7 : 1,
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                  transition: "opacity 150ms ease",
                }}
              >
                {state === "loading" ? "Subscribing…" : "Subscribe →"}
              </button>
            </div>

            {/* Error message */}
            {errorMsg && (
              <p
                id="subscribe-error"
                role="alert"
                style={{
                  marginTop: "8px",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "13px",
                  color: "#EF4444",
                  textAlign: "left",
                }}
              >
                {errorMsg}
              </p>
            )}

            {/* Tag preference selector — appears after user starts typing */}
            {showTagPrefs && (
              <div style={{ marginTop: "20px", textAlign: "left" }}>
                <p
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "13px",
                    fontWeight: 500,
                    color: "var(--color-text-secondary)",
                    marginBottom: "10px",
                  }}
                >
                  What kind of work are you interested in?{" "}
                  <span style={{ fontWeight: 400 }}>(optional)</span>
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {ALL_CONTRIBUTION_TYPES.map((type) => (
                    <Tag
                      key={type}
                      type={type}
                      label={formatContributionType(type)}
                      size="sm"
                      selected={tagPrefs.includes(type)}
                      onClick={() => toggleTag(type)}
                    />
                  ))}
                </div>
              </div>
            )}
          </form>
        )}
      </div>
      </div>

    </section>
  );
}
