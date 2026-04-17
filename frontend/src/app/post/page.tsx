"use client";

/**
 * Post a Task page — /post
 *
 * Allows maintainers to manually list a non-code task on Nocos.
 * Tasks go live immediately after submission and follow the same
 * 14-day staleness rule as scraped tasks (features.md §7).
 *
 * Layout:
 *   Desktop — two columns: form on the left, live card preview on the right.
 *   Mobile  — single column: form on top, preview panel below.
 *
 * Form fields (in order):
 *   1. GitHub Repo URL  — auto-fetches project info on blur
 *   2. Issue Title      — required, max 100 chars, character counter
 *   3. Description      — required, min 50 chars, character counter
 *   4. Contribution Type — multi-select tag picker (11 types)
 *   5. GitHub Issue URL — optional
 *   6. Paid / Unpaid    — toggle; when Paid, shows optional amount input
 *   7. Difficulty       — radio: Beginner / Intermediate / Advanced
 *
 * Submission:
 *   - Validates all required fields before allowing submit.
 *   - Shows field-level inline errors on blur.
 *   - On success: replaces form with confirmation message + task preview.
 *   - On error: shows error banner, keeps form filled.
 *
 * description_original is never rendered — only description_display from the API
 * response (SKILLS.md §16).
 */

import { useState, useRef } from "react";
import { Check } from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { Tag } from "@/components/ui/tag";
import { PreviewPanel } from "@/components/post-task/preview-panel";
import { fetchRepoPreview, submitTask } from "@/lib/api";
import type { RepoPreview } from "@/lib/api";

// ── Contribution types shown in the multi-select picker ──────────────────────
// "paid" and "beginner" are excluded — those have dedicated form fields.
const PICKER_TYPES = [
  "design",
  "documentation",
  "pr_review",
  "data_analytics",
  "translation",
  "research",
  "community",
  "marketing",
  "social_media",
  "project_management",
  "hacktoberfest",
] as const;

// GitHub repo URL validation pattern (SKILLS.md §16)
const GITHUB_REPO_RE = /^https:\/\/github\.com\/[^/]+\/[^/]+\/?$/;
const GITHUB_ISSUE_RE = /^https:\/\/github\.com\/.+\/issues\/\d+$/;

// ── Types ─────────────────────────────────────────────────────────────────────

type Difficulty = "beginner" | "intermediate" | "advanced";

// Simple email format check — backend validates too
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface FormErrors {
  repoUrl?: string;
  title?: string;
  description?: string;
  contributionTypes?: string;
  email?: string;
}

const DIFFICULTY_OPTIONS: Array<{
  value: Difficulty;
  label: string;
  hint: string;
}> = [
  {
    value: "beginner",
    label: "Beginner",
    hint: "No prior OSS contribution needed",
  },
  {
    value: "intermediate",
    label: "Intermediate",
    hint: "Some experience with the project helps",
  },
  {
    value: "advanced",
    label: "Advanced",
    hint: "Deep familiarity with the project required",
  },
];

// ── Page component ────────────────────────────────────────────────────────────

export default function PostTaskPage() {
  // ── Repo URL state ────────────────────────────────────────────────────────
  const [repoUrl, setRepoUrl] = useState("");
  const [repoPreview, setRepoPreview] = useState<RepoPreview | null>(null);
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoFetchError, setRepoFetchError] = useState<string | null>(null);

  // ── Core form state ───────────────────────────────────────────────────────
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [githubIssueUrl, setGithubIssueUrl] = useState("");
  const [isPaid, setIsPaid] = useState(false);
  const [paidAmount, setPaidAmount] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("beginner");

  // ── Validation state ──────────────────────────────────────────────────────
  const [errors, setErrors] = useState<FormErrors>({});

  // ── Email state ───────────────────────────────────────────────────────────
  const [email, setEmail] = useState("");

  // ── Submission state ──────────────────────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);

  // Ref for the description textarea so we can track blur
  const descRef = useRef<HTMLTextAreaElement>(null);

  // ── Repo URL auto-fetch ───────────────────────────────────────────────────

  /**
   * Fired when the repo URL input loses focus.
   * Validates the URL pattern, then calls the preview endpoint if valid.
   */
  async function handleRepoUrlBlur() {
    const trimmed = repoUrl.trim();
    if (!trimmed) return;

    if (!GITHUB_REPO_RE.test(trimmed)) {
      setErrors((prev) => ({
        ...prev,
        repoUrl: "Please enter a valid GitHub repo URL (https://github.com/owner/repo)",
      }));
      return;
    }

    setErrors((prev) => ({ ...prev, repoUrl: undefined }));
    setRepoFetchError(null);
    setRepoLoading(true);

    try {
      const preview = await fetchRepoPreview(trimmed);
      setRepoPreview(preview);
    } catch {
      setRepoFetchError(
        "Couldn't find this repo. Check the URL and try again."
      );
      setRepoPreview(null);
    } finally {
      setRepoLoading(false);
    }
  }

  // ── Field-level validation on blur ────────────────────────────────────────

  function validateTitle() {
    if (!title.trim()) {
      setErrors((prev) => ({ ...prev, title: "Title is required" }));
    } else {
      setErrors((prev) => ({ ...prev, title: undefined }));
    }
  }

  function validateDescription() {
    if (!description.trim()) {
      setErrors((prev) => ({
        ...prev,
        description: "Description is required",
      }));
    } else if (description.trim().length < 50) {
      setErrors((prev) => ({
        ...prev,
        description: `Description must be at least 50 characters (${description.trim().length}/50)`,
      }));
    } else {
      setErrors((prev) => ({ ...prev, description: undefined }));
    }
  }

  // ── Contribution type toggle ──────────────────────────────────────────────

  function toggleType(type: string) {
    setSelectedTypes((prev) => {
      const next = prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type];
      // Clear the type error as soon as at least one is selected
      if (next.length > 0) {
        setErrors((e) => ({ ...e, contributionTypes: undefined }));
      }
      return next;
    });
  }

  // ── Full form validation before submit ────────────────────────────────────

  function validateAll(): boolean {
    const next: FormErrors = {};
    if (!repoUrl.trim() || !GITHUB_REPO_RE.test(repoUrl.trim())) {
      next.repoUrl = "A valid GitHub repo URL is required";
    }
    if (!title.trim()) next.title = "Title is required";
    if (title.trim().length > 100) next.title = "Title must be 100 characters or fewer";
    if (!description.trim()) next.description = "Description is required";
    if (description.trim().length < 50) {
      next.description = `Description must be at least 50 characters (${description.trim().length}/50)`;
    }
    if (selectedTypes.length === 0) {
      next.contributionTypes = "Select at least one contribution type";
    }
    if (!email.trim() || !EMAIL_RE.test(email.trim())) {
      next.email = "Please enter a valid email address.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  // ── Form submission ───────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validateAll()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // First selected type becomes contribution_type (the DB field is single-value).
      // Any additional selected types are included as labels by the backend.
      const primaryType = selectedTypes[0];

      const result = await submitTask({
        github_repo_url: repoUrl.trim(),
        title: title.trim(),
        description: description.trim(),
        contribution_type: primaryType,
        is_paid: isPaid,
        paid_amount: isPaid && paidAmount.trim() ? paidAmount.trim() : undefined,
        difficulty,
        github_issue_url: githubIssueUrl.trim() || undefined,
        submitter_email: email.trim(),
      });

      setSuccessId(result.id);
    } catch {
      setSubmitError("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  // ── Success state ─────────────────────────────────────────────────────────

  if (successId) {
    return (
      <>
        <Navbar />
        <PageShell>
        <div
          style={{
            maxWidth: "600px",
            margin: "0 auto",
            padding: "80px 24px",
            textAlign: "center",
          }}
        >
          {/* Success icon */}
          <div
            aria-hidden="true"
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              backgroundColor: "var(--color-status-active)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 24px",
            }}
          >
            <Check size={24} strokeWidth={2.5} color="#ffffff" />
          </div>

          <h1
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "clamp(1.5rem, 4vw, 2rem)",
              color: "var(--color-text-primary)",
              marginBottom: "12px",
            }}
          >
            Task submitted for review.
          </h1>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--color-text-secondary)",
              marginBottom: "36px",
              lineHeight: 1.6,
            }}
          >
            Your task is in the moderation queue. Once approved it will be
            visible to contributors and remain active for 14 days.
            We may follow up at the email address you provided.
          </p>

          {/* CTAs */}
          <div
            style={{
              display: "flex",
              gap: "12px",
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <Link
              href={`/tasks/${successId}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "12px 24px",
                backgroundColor: "var(--color-cta-primary)",
                color: "#ffffff",
                fontFamily: "'Inter', sans-serif",
                fontWeight: 600,
                fontSize: "0.9375rem",
                borderRadius: "10px",
                textDecoration: "none",
                transition: "opacity 150ms ease",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLElement).style.opacity = "0.88")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLElement).style.opacity = "1")
              }
            >
              View your task →
            </Link>
            <button
              onClick={() => {
                // Reset all form state for a fresh submission
                setRepoUrl("");
                setRepoPreview(null);
                setRepoFetchError(null);
                setTitle("");
                setDescription("");
                setSelectedTypes([]);
                setGithubIssueUrl("");
                setIsPaid(false);
                setPaidAmount("");
                setDifficulty("beginner");
                setEmail("");
                setErrors({});
                setSubmitError(null);
                setSuccessId(null);
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "12px 24px",
                backgroundColor: "transparent",
                color: "var(--color-text-primary)",
                fontFamily: "'Inter', sans-serif",
                fontWeight: 600,
                fontSize: "0.9375rem",
                borderRadius: "10px",
                border: "1px solid var(--color-border)",
                cursor: "pointer",
                transition: "border-color 150ms ease",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLElement).style.borderColor =
                  "var(--color-text-secondary)")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLElement).style.borderColor =
                  "var(--color-border)")
              }
            >
              Post another task
            </button>
          </div>
        </div>
      </PageShell>
      </>
    );
  }

  // ── Main form render ──────────────────────────────────────────────────────

  // Primary contribution type for the live preview (first selected, or "design")
  const previewType = selectedTypes[0] ?? "design";

  return (
    <>
      <Navbar />
      <PageShell>
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "48px 24px 80px",
        }}
      >
        {/* Page header */}
        <div style={{ marginBottom: "40px" }}>
          <h1
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 700,
              fontSize: "clamp(1.5rem, 4vw, 2.25rem)",
              color: "var(--color-text-primary)",
              margin: "0 0 12px",
            }}
          >
            Post a Task
          </h1>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              lineHeight: 1.6,
              color: "var(--color-text-secondary)",
              margin: 0,
              maxWidth: "520px",
            }}
          >
            Have a non-code task that needs doing? List it on Nocos and reach
            contributors who can help.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="post-layout">
          {/* ── Left column: Form ─────────────────────────────────────── */}
          <form
            onSubmit={handleSubmit}
            noValidate
            style={{ display: "flex", flexDirection: "column", gap: "28px" }}
          >
            {/* Error banner */}
            {submitError && (
              <div
                role="alert"
                style={{
                  padding: "14px 16px",
                  borderRadius: "8px",
                  border: "1px solid var(--color-status-inactive)",
                  backgroundColor: "var(--color-surface)",
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "0.9375rem",
                  color: "var(--color-status-inactive)",
                }}
              >
                {submitError}
              </div>
            )}

            {/* ── GitHub Repo URL ─────────────────────────────────────── */}
            <FieldGroup
              id="repo-url"
              label="GitHub Repo URL"
              required
              error={errors.repoUrl ?? repoFetchError ?? undefined}
            >
              <div style={{ position: "relative" }}>
                <input
                  id="repo-url"
                  type="url"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    // Clear errors on change so the user gets immediate feedback
                    setErrors((prev) => ({ ...prev, repoUrl: undefined }));
                    setRepoFetchError(null);
                    setRepoPreview(null);
                  }}
                  onBlur={handleRepoUrlBlur}
                  placeholder="https://github.com/org/repo"
                  aria-describedby={
                    errors.repoUrl || repoFetchError
                      ? "repo-url-error"
                      : "repo-url-hint"
                  }
                  aria-invalid={!!(errors.repoUrl || repoFetchError)}
                  style={{
                    ...inputStyle,
                    paddingRight: repoLoading ? "40px" : undefined,
                  }}
                />
                {/* Spinner while fetching repo info */}
                {repoLoading && (
                  <div
                    aria-hidden="true"
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                    }}
                  >
                    <Spinner />
                  </div>
                )}
                {/* Green checkmark when repo is found */}
                {!repoLoading && repoPreview && (
                  <div
                    aria-hidden="true"
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      color: "var(--color-status-active)",
                    }}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                )}
              </div>
              {/* Repo preview name — shown after a successful fetch */}
              {repoPreview && !repoLoading && (
                <p
                  id="repo-url-hint"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "13px",
                    color: "var(--color-status-active)",
                    margin: "6px 0 0",
                  }}
                >
                  Found: {repoPreview.name}
                </p>
              )}
            </FieldGroup>

            {/* ── Issue Title ─────────────────────────────────────────── */}
            <FieldGroup
              id="issue-title"
              label="Issue Title"
              required
              error={errors.title}
              counter={{ current: title.length, max: 100 }}
            >
              <input
                id="issue-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value.slice(0, 100))}
                onBlur={validateTitle}
                placeholder="e.g. Design a new contributor onboarding flow"
                aria-describedby={errors.title ? "issue-title-error" : undefined}
                aria-invalid={!!errors.title}
                maxLength={100}
                style={inputStyle}
              />
            </FieldGroup>

            {/* ── Description ─────────────────────────────────────────── */}
            <FieldGroup
              id="issue-description"
              label="Description"
              required
              error={errors.description}
              counter={{ current: description.length, min: 50 }}
              hint="Write this for a non-technical contributor. Describe what they'll actually be doing."
            >
              <textarea
                id="issue-description"
                ref={descRef}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onBlur={validateDescription}
                placeholder="Describe the task in plain language — no technical jargon needed. What will the contributor actually do?"
                aria-describedby={
                  errors.description
                    ? "issue-description-error"
                    : "issue-description-hint"
                }
                aria-invalid={!!errors.description}
                rows={5}
                style={{
                  ...inputStyle,
                  resize: "vertical",
                  minHeight: "120px",
                  lineHeight: 1.6,
                }}
              />
            </FieldGroup>

            {/* ── Contribution Type ───────────────────────────────────── */}
            <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
              <legend
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  color: "var(--color-text-primary)",
                  marginBottom: "10px",
                  display: "block",
                }}
              >
                Contribution Type
                <span
                  aria-hidden="true"
                  style={{ color: "var(--color-status-inactive)", marginLeft: "4px" }}
                >
                  *
                </span>
              </legend>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                  marginBottom: errors.contributionTypes ? "8px" : "0",
                }}
                aria-describedby={
                  errors.contributionTypes ? "contribution-type-error" : undefined
                }
              >
                {PICKER_TYPES.map((type) => (
                  <Tag
                    key={type}
                    type={type}
                    size="md"
                    selected={selectedTypes.includes(type)}
                    onClick={() => toggleType(type)}
                  />
                ))}
              </div>

              {errors.contributionTypes && (
                <p
                  id="contribution-type-error"
                  role="alert"
                  style={errorTextStyle}
                >
                  {errors.contributionTypes}
                </p>
              )}
            </fieldset>

            {/* ── GitHub Issue URL (optional) ─────────────────────────── */}
            <FieldGroup
              id="github-issue-url"
              label="GitHub Issue URL (optional)"
            >
              <input
                id="github-issue-url"
                type="url"
                value={githubIssueUrl}
                onChange={(e) => setGithubIssueUrl(e.target.value)}
                placeholder="https://github.com/org/repo/issues/123"
                style={inputStyle}
              />
            </FieldGroup>

            {/* ── Paid / Unpaid ───────────────────────────────────────── */}
            <div>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  color: "var(--color-text-primary)",
                  margin: "0 0 10px",
                }}
              >
                Compensation
              </p>

              {/* Toggle buttons */}
              <div
                style={{
                  display: "inline-flex",
                  borderRadius: "8px",
                  border: "1px solid var(--color-border)",
                  overflow: "hidden",
                }}
                role="group"
                aria-label="Compensation type"
              >
                {[
                  { value: false, label: "Unpaid" },
                  { value: true, label: "Paid" },
                ].map(({ value, label }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setIsPaid(value)}
                    aria-pressed={isPaid === value}
                    style={{
                      padding: "8px 20px",
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 500,
                      fontSize: "0.875rem",
                      cursor: "pointer",
                      border: "none",
                      backgroundColor:
                        isPaid === value
                          ? "var(--color-cta-primary)"
                          : "transparent",
                      color: isPaid === value ? "#ffffff" : "var(--color-text-secondary)",
                      transition: "background-color 150ms ease, color 150ms ease",
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {/* Amount input — visible only when Paid is selected */}
              {isPaid && (
                <div style={{ marginTop: "12px" }}>
                  <label
                    htmlFor="paid-amount"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: "0.8125rem",
                      color: "var(--color-text-secondary)",
                      display: "block",
                      marginBottom: "6px",
                    }}
                  >
                    Amount / details (optional)
                  </label>
                  <input
                    id="paid-amount"
                    type="text"
                    value={paidAmount}
                    onChange={(e) => setPaidAmount(e.target.value)}
                    placeholder="e.g. $50 bounty, €200 for completion"
                    maxLength={100}
                    style={{ ...inputStyle, maxWidth: "320px" }}
                  />
                </div>
              )}
            </div>

            {/* ── Difficulty ──────────────────────────────────────────── */}
            <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
              <legend
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  color: "var(--color-text-primary)",
                  marginBottom: "12px",
                  display: "block",
                }}
              >
                Difficulty
              </legend>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {DIFFICULTY_OPTIONS.map(({ value, label, hint }) => {
                  const isSelected = difficulty === value;
                  return (
                    <label
                      key={value}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "12px",
                        cursor: "pointer",
                        padding: "12px 14px",
                        borderRadius: "8px",
                        border: `1px solid ${isSelected ? "var(--color-cta-primary)" : "var(--color-border)"}`,
                        backgroundColor: isSelected
                          ? "var(--color-surface)"
                          : "transparent",
                        transition: "border-color 150ms ease",
                      }}
                    >
                      <input
                        type="radio"
                        name="difficulty"
                        value={value}
                        checked={isSelected}
                        onChange={() => setDifficulty(value)}
                        style={{ marginTop: "2px", accentColor: "var(--color-cta-primary)" }}
                      />
                      <div>
                        <span
                          style={{
                            fontFamily: "'Inter', sans-serif",
                            fontWeight: 600,
                            fontSize: "0.875rem",
                            color: "var(--color-text-primary)",
                            display: "block",
                          }}
                        >
                          {label}
                        </span>
                        <span
                          style={{
                            fontFamily: "'Inter', sans-serif",
                            fontSize: "0.8125rem",
                            color: "var(--color-text-secondary)",
                          }}
                        >
                          {hint}
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            {/* ── Submitter email ─────────────────────────────────────── */}
            <FieldGroup
              id="submitter-email"
              label="Your email address"
              required
              error={errors.email}
              hint="Used only to follow up on your submission. Never shown publicly."
            >
              <input
                id="submitter-email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setErrors((prev) => ({ ...prev, email: undefined }));
                }}
                onBlur={() => {
                  if (!email.trim() || !EMAIL_RE.test(email.trim())) {
                    setErrors((prev) => ({
                      ...prev,
                      email: "Please enter a valid email address.",
                    }));
                  }
                }}
                placeholder="you@example.com"
                required
                aria-describedby={errors.email ? "submitter-email-error" : "submitter-email-hint"}
                aria-invalid={!!errors.email}
                style={inputStyle}
              />
            </FieldGroup>

            {/* ── Submit button ───────────────────────────────────────── */}
            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  padding: "14px 32px",
                  backgroundColor: isSubmitting
                    ? "var(--color-border)"
                    : "var(--color-cta-primary)",
                  color: isSubmitting
                    ? "var(--color-text-secondary)"
                    : "#ffffff",
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600,
                  fontSize: "1rem",
                  borderRadius: "10px",
                  border: "none",
                  cursor: isSubmitting ? "not-allowed" : "pointer",
                  transition: "opacity 150ms ease, background-color 150ms ease",
                  width: "100%",
                }}
                onMouseEnter={(e) => {
                  if (!isSubmitting) {
                    (e.currentTarget as HTMLElement).style.opacity = "0.88";
                  }
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.opacity = "1";
                }}
              >
                {isSubmitting ? (
                  <>
                    <Spinner />
                    Posting…
                  </>
                ) : (
                  "Post Task →"
                )}
              </button>
            </div>
          </form>

          {/* ── Right column: Live preview ─────────────────────────── */}
          <div className="preview-column">
            <PreviewPanel
              title={title}
              description={description}
              projectName={repoPreview?.name ?? ""}
              projectAvatarUrl={repoPreview?.avatar_url ?? ""}
              contributionType={previewType}
              isPaid={isPaid}
              difficulty={difficulty}
            />
          </div>
        </div>
      </div>

    </PageShell>
    </>
  );
}

// ── Shared layout shell ───────────────────────────────────────────────────────

/**
 * PageShell — provides the background colour and min-height so the page
 * never looks empty during loading or the success state.
 */
function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--color-bg)",
        paddingTop: "var(--navbar-height)",
      }}
    >
      {children}
    </div>
  );
}

// ── FieldGroup helper ─────────────────────────────────────────────────────────

interface FieldGroupProps {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  counter?: { current: number; max?: number; min?: number };
  children: React.ReactNode;
}

/**
 * FieldGroup — wraps an input with a label, optional hint text, inline error
 * message, and optional character counter. Wires aria-describedby so the
 * error is announced to screen readers (SKILLS.md §10).
 *
 * Pass required={true} to render a red asterisk after the label text.
 */
function FieldGroup({
  id,
  label,
  required,
  error,
  hint,
  counter,
  children,
}: FieldGroupProps) {
  return (
    <div>
      {/* Label + optional counter on the same row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "6px",
        }}
      >
        <label
          htmlFor={id}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontWeight: 600,
            fontSize: "0.875rem",
            color: "var(--color-text-primary)",
          }}
        >
          {label}
          {required && (
            <span
              aria-hidden="true"
              style={{ color: "var(--color-status-inactive)", marginLeft: "3px" }}
            >
              *
            </span>
          )}
        </label>
        {counter && (
          <span
            aria-hidden="true"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "12px",
              color:
                counter.min !== undefined && counter.current < counter.min
                  ? "var(--color-status-inactive)"
                  : "var(--color-text-secondary)",
            }}
          >
            {counter.min !== undefined
              ? `${counter.current} / ${counter.min} min`
              : `${counter.current} / ${counter.max}`}
          </span>
        )}
      </div>

      {children}

      {/* Hint text — shown when there is no error */}
      {hint && !error && (
        <p
          id={`${id}-hint`}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "12px",
            color: "var(--color-text-secondary)",
            margin: "6px 0 0",
            lineHeight: 1.5,
          }}
        >
          {hint}
        </p>
      )}

      {/* Inline error message — linked to input via aria-describedby */}
      {error && (
        <p
          id={`${id}-error`}
          role="alert"
          style={errorTextStyle}
        >
          {error}
        </p>
      )}
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────

/**
 * Spinner — small animated loading indicator used inside the repo URL input
 * and the submit button.
 */
function Spinner() {
  return (
    <>
      <span
        aria-hidden="true"
        style={{
          display: "inline-block",
          width: "14px",
          height: "14px",
          borderRadius: "50%",
          border: "2px solid var(--color-border)",
          borderTopColor: "var(--color-cta-primary)",
          animation: "spin 0.7s linear infinite",
          flexShrink: 0,
        }}
      />
    </>
  );
}

// ── Shared style objects ──────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  boxSizing: "border-box",
  padding: "10px 12px",
  fontFamily: "'Inter', sans-serif",
  fontSize: "0.9375rem",
  color: "var(--color-text-primary)",
  backgroundColor: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "8px",
  outline: "none",
  transition: "border-color 150ms ease",
};

const errorTextStyle: React.CSSProperties = {
  fontFamily: "'Inter', sans-serif",
  fontSize: "12px",
  color: "var(--color-status-inactive)",
  margin: "6px 0 0",
};
