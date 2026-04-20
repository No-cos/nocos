// types.ts — IssueCard component props

export interface IssueCardIssue {
  id: string;
  title: string;
  ai_title: string | null;
  description_display: string;
  is_ai_generated: boolean;
  contribution_type: string;
  labels: string[];
  is_paid: boolean;
  is_bounty: boolean;
  bounty_amount: number | null;
  difficulty?: string | null;
  github_issue_url: string;
  github_created_at?: string | null;
  project: {
    id: string;
    name: string;
    avatar_url: string;
    activity_status: "active" | "slow" | "inactive";
  };
}

export interface IssueCardProps {
  issue: IssueCardIssue;
  /** Called when the card is clicked — typically navigates to /tasks/[id] */
  onClick?: () => void;
  /** Position in the grid — drives the entrance stagger delay (0-based, capped at 5) */
  animationIndex?: number;
}
