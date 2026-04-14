// types.ts — IssueCard component props

export interface IssueCardIssue {
  id: string;
  title: string;
  description_display: string;
  is_ai_generated: boolean;
  contribution_type: string;
  labels: string[];
  is_paid: boolean;
  difficulty?: string | null;
  github_issue_url: string;
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
}
