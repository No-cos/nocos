/**
 * PreviewPanel component — live card preview for the Post a Task form.
 *
 * Renders an IssueCard populated with the current form values so the
 * maintainer can see exactly how their task will appear to contributors
 * before they submit.
 *
 * Behaviour:
 * - Updates in real time as the maintainer types (no debounce needed —
 *   this is local state only, not an API call).
 * - If the title is empty, shows placeholder text in the card title slot.
 * - If the description is empty, shows placeholder text in the card desc slot.
 * - If the avatar has not loaded yet (repo not yet previewed), shows a
 *   placeholder circle in the project avatar slot.
 *
 * Layout:
 * - Section label at the top.
 * - IssueCard rendered inside a constrained container so it matches the
 *   real grid appearance.
 *
 * All colours via CSS variables — no hardcoded hex values.
 *
 * @param title            - Current issue title from the form
 * @param description      - Current description from the form
 * @param projectName      - Project name from the repo preview response
 * @param projectAvatarUrl - Project avatar URL from the repo preview response
 * @param contributionType - Primary selected contribution type (or "design" as default)
 * @param isPaid           - Whether the task is marked as paid
 * @param difficulty       - Selected difficulty level
 */

import { IssueCard } from "@/components/issue-card";
import type { IssueCardIssue } from "@/components/issue-card/types";

interface PreviewPanelProps {
  title: string;
  description: string;
  projectName: string;
  projectAvatarUrl: string;
  contributionType: string;
  isPaid: boolean;
  difficulty: "beginner" | "intermediate" | "advanced";
}

// Placeholder strings shown in the card when the maintainer hasn't typed yet
const PLACEHOLDER_TITLE = "Your issue title will appear here";
const PLACEHOLDER_DESC = "Your description will appear here — write for a non-technical contributor.";
const PLACEHOLDER_PROJECT = "Your project";

export function PreviewPanel({
  title,
  description,
  projectName,
  projectAvatarUrl,
  contributionType,
  isPaid,
  difficulty,
}: PreviewPanelProps) {
  // Construct a mock Issue object that IssueCard can render.
  // We use placeholder text when fields are empty so the card never looks broken.
  const previewIssue: IssueCardIssue = {
    id: "preview",
    title: title.trim() || PLACEHOLDER_TITLE,
    description_display: description.trim() || PLACEHOLDER_DESC,
    is_ai_generated: false,
    contribution_type: contributionType || "design",
    labels: [],
    is_paid: isPaid,
    is_bounty: false,
    bounty_amount: null,
    difficulty: difficulty,
    github_issue_url: "#",
    project: {
      id: "preview-project",
      name: projectName.trim() || PLACEHOLDER_PROJECT,
      avatar_url: projectAvatarUrl,
      activity_status: "active",
    },
  };

  return (
    <div>
      {/* Section label */}
      <p
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--color-text-secondary)",
          margin: "0 0 16px",
        }}
      >
        Preview — how contributors will see this
      </p>

      {/* Card container — max-width matches a grid column at desktop */}
      <div style={{ maxWidth: "340px" }}>
        {/*
          onClick is intentionally omitted so the preview card is not
          interactive — it's purely visual feedback for the maintainer.
        */}
        <IssueCard issue={previewIssue} />
      </div>

      {/* Helper note below the card */}
      <p
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "12px",
          color: "var(--color-text-secondary)",
          margin: "12px 0 0",
          lineHeight: 1.5,
        }}
      >
        This is how your task will appear on the discovery grid.
      </p>
    </div>
  );
}
