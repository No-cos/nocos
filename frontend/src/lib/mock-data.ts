/**
 * mock-data.ts
 *
 * Realistic mock issues used in development when the backend is not running.
 * This data is ONLY used in development mode (NODE_ENV === "development") and
 * only when the real API call fails. It is never shipped to production.
 *
 * To disable mock data and use the real backend, start the backend server:
 *   cd backend && uvicorn main:app --reload
 */

import { type IssueListResponse, type Issue, type Project } from "./api";

export interface IssueDetail extends Issue {
  project: Project;
}

const MOCK_ISSUES: Issue[] = [
  {
    id: "mock-1",
    project_id: "proj-1",
    project: {
      name: "CHAOSS",
      avatar_url: "https://avatars.githubusercontent.com/u/29740296?v=4",
      activity_status: "active",
    },
    title: "Improve the onboarding flow for new design contributors",
    description_display:
      "Help redesign the welcome experience for designers joining the CHAOSS community. You will review the current onboarding steps and suggest clearer visual guidance to help contributors find their first task faster.",
    is_ai_generated: false,
    labels: ["design", "good-first-issue"],
    contribution_type: "design",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/chaoss/grimoirelab/issues/1",
    github_created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-2",
    project_id: "proj-2",
    project: {
      name: "Mozilla",
      avatar_url: "https://avatars.githubusercontent.com/u/131524?v=4",
      activity_status: "active",
    },
    title: "Write documentation for the contributor handbook",
    description_display:
      "Mozilla needs clear, friendly documentation for its contributor handbook. You will write step-by-step guides explaining how to join the project, pick tasks, and submit work — written for a non-technical audience.",
    is_ai_generated: false,
    labels: ["documentation", "help-wanted"],
    contribution_type: "documentation",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/mozilla/inclusion/issues/2",
    github_created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-3",
    project_id: "proj-3",
    project: {
      name: "Open Source Design",
      avatar_url: "https://avatars.githubusercontent.com/u/7833980?v=4",
      activity_status: "active",
    },
    title: "Translate the design contribution guide to French",
    description_display:
      "The Open Source Design contribution guide needs to be translated into French to reach a wider community. You will translate the existing English guide, ensuring the tone stays friendly and accessible.",
    is_ai_generated: true,
    labels: ["translation", "good-first-issue"],
    contribution_type: "translation",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/opensourcedesign/jobs/issues/3",
    github_created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-4",
    project_id: "proj-4",
    project: {
      name: "Ushahidi",
      avatar_url: "https://avatars.githubusercontent.com/u/203776?v=4",
      activity_status: "slow",
    },
    title: "Review and improve accessibility of the platform UI",
    description_display:
      "Ushahidi is looking for someone to audit the platform's interface for accessibility issues. You will review screen layouts, colour contrast, and keyboard navigation and document your findings in a short report.",
    is_ai_generated: false,
    labels: ["a11y", "design", "help-wanted"],
    contribution_type: "design",
    is_paid: true,
    difficulty: "intermediate",
    source: "manual_post",
    github_issue_url: "https://github.com/ushahidi/platform/issues/4",
    github_created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-5",
    project_id: "proj-5",
    project: {
      name: "Wikimedia",
      avatar_url: "https://avatars.githubusercontent.com/u/146641?v=4",
      activity_status: "active",
    },
    title: "Write social media content for the Hacktoberfest campaign",
    description_display:
      "Wikimedia needs engaging social media posts to promote their Hacktoberfest participation. You will draft a series of posts for Twitter/X and LinkedIn that highlight non-technical contribution opportunities.",
    is_ai_generated: false,
    labels: ["marketing", "content", "hacktoberfest"],
    contribution_type: "marketing",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/wikimedia/design/issues/5",
    github_created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-6",
    project_id: "proj-6",
    project: {
      name: "Apache Software Foundation",
      avatar_url: "https://avatars.githubusercontent.com/u/47359?v=4",
      activity_status: "active",
    },
    title: "Conduct user research interviews with new contributors",
    description_display:
      "Help Apache understand why new contributors drop off during onboarding. You will conduct 5–8 short interviews with recent contributors, write up key themes, and share your findings with the community team.",
    is_ai_generated: false,
    labels: ["research", "community"],
    contribution_type: "research",
    is_paid: false,
    difficulty: "intermediate",
    source: "github_scrape",
    github_issue_url: "https://github.com/apache/www-site/issues/6",
    github_created_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-7",
    project_id: "proj-7",
    project: {
      name: "Nextcloud",
      avatar_url: "https://avatars.githubusercontent.com/u/19211038?v=4",
      activity_status: "active",
    },
    title: "Review pull requests for clarity and completeness",
    description_display:
      "Nextcloud needs reviewers to check that pull request descriptions are clear and complete before merging. You will read PR descriptions, flag missing context, and suggest improvements — no coding knowledge required.",
    is_ai_generated: true,
    labels: ["pr-review", "help-wanted"],
    contribution_type: "pr_review",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/nextcloud/server/issues/7",
    github_created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-8",
    project_id: "proj-8",
    project: {
      name: "Grafana",
      avatar_url: "https://avatars.githubusercontent.com/u/7195757?v=4",
      activity_status: "active",
    },
    title: "Analyse and document dashboard usage patterns",
    description_display:
      "Grafana wants to understand how users interact with dashboards. You will analyse publicly available usage data, identify common patterns, and present your findings in a clear summary document.",
    is_ai_generated: false,
    labels: ["data", "documentation"],
    contribution_type: "data_analytics",
    is_paid: true,
    difficulty: "intermediate",
    source: "manual_post",
    github_issue_url: "https://github.com/grafana/grafana/issues/8",
    github_created_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-9",
    project_id: "proj-1",
    project: {
      name: "CHAOSS",
      avatar_url: "https://avatars.githubusercontent.com/u/29740296?v=4",
      activity_status: "active",
    },
    title: "Create visual explainers for the Badging Initiative",
    description_display:
      "The CHAOSS Badging Initiative needs simple visual explainers to help projects understand what each badge means. You will design 3–5 infographic-style illustrations that can be shared on social media and documentation.",
    is_ai_generated: false,
    labels: ["design", "community"],
    contribution_type: "design",
    is_paid: false,
    difficulty: "intermediate",
    source: "github_scrape",
    github_issue_url: "https://github.com/chaoss/grimoirelab/issues/9",
    github_created_at: new Date(Date.now() - 9 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-10",
    project_id: "proj-9",
    project: {
      name: "Django",
      avatar_url: "https://avatars.githubusercontent.com/u/27804?v=4",
      activity_status: "active",
    },
    title: "Improve community management for the Django forum",
    description_display:
      "Django's community forum needs help with moderation, welcoming new members, and surfacing unanswered questions. You will spend a few hours each week helping keep the forum friendly and organised.",
    is_ai_generated: false,
    labels: ["community", "help-wanted"],
    contribution_type: "community",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/django/django/issues/10",
    github_created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-11",
    project_id: "proj-10",
    project: {
      name: "Linux Foundation",
      avatar_url: "https://avatars.githubusercontent.com/u/1864969?v=4",
      activity_status: "slow",
    },
    title: "Design a landing page for the new contributor portal",
    description_display:
      "The Linux Foundation is building a new contributor portal and needs a landing page design. You will create wireframes and a high-fidelity mockup in Figma, following the existing brand guidelines.",
    is_ai_generated: false,
    labels: ["design", "ui", "good-first-issue"],
    contribution_type: "design",
    is_paid: true,
    difficulty: "advanced",
    source: "manual_post",
    github_issue_url: "https://github.com/lf-edge/edge-home-orchestration-go/issues/11",
    github_created_at: new Date(Date.now() - 11 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "mock-12",
    project_id: "proj-11",
    project: {
      name: "Open Food Facts",
      avatar_url: "https://avatars.githubusercontent.com/u/1799923?v=4",
      activity_status: "active",
    },
    title: "Translate product category labels to Swahili",
    description_display:
      "Open Food Facts needs product category labels translated into Swahili to support East African users. You will translate a list of approximately 200 food category names and verify accuracy with native speakers if possible.",
    is_ai_generated: true,
    labels: ["translation", "good-first-issue"],
    contribution_type: "translation",
    is_paid: false,
    difficulty: "beginner",
    source: "github_scrape",
    github_issue_url: "https://github.com/openfoodfacts/openfoodfacts-server/issues/12",
    github_created_at: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

/**
 * Looks up a single issue from mock data by ID and returns it as an IssueDetail
 * with a full Project object attached. Returns null if the ID is not found.
 *
 * Used by useIssue.ts when the backend is offline in development.
 */
export function getMockIssue(id: string): IssueDetail | null {
  const issue = MOCK_ISSUES.find((i) => i.id === id);
  if (!issue) return null;

  const githubUrl = issue.github_issue_url.replace(/\/issues\/\d+$/, "");
  const urlParts = githubUrl.replace("https://github.com/", "").split("/");
  const owner = urlParts[0] ?? "org";
  const repo = urlParts[1] ?? "repo";

  const project: Project = {
    id: issue.project_id,
    name: issue.project.name,
    github_url: githubUrl,
    github_owner: owner,
    github_repo: repo,
    description: "An open source project.",
    website_url: null,
    avatar_url: issue.project.avatar_url,
    social_links: {
      twitter: null,
      discord: null,
      slack: null,
      linkedin: null,
      youtube: null,
      github: githubUrl,
    },
    activity_score: 80,
    activity_status: issue.project.activity_status,
    last_commit_date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  return { ...issue, project };
}

/**
 * Returns a mock IssueListResponse shaped exactly like the real API response.
 * Supports basic filtering by contribution_type and title search so the
 * filter bar and search bar work correctly in development.
 */
export function getMockIssues(options: {
  page?: number;
  limit?: number;
  type?: string;
  types?: string;
  search?: string;
}): IssueListResponse {
  const { page = 1, limit = 12, type, types, search } = options;

  let filtered = [...MOCK_ISSUES];

  // Filter by contribution type(s)
  const typeList = types
    ? types.split(",").map((t) => t.trim())
    : type
    ? [type]
    : [];

  if (typeList.length > 0) {
    filtered = filtered.filter((issue) =>
      typeList.includes(issue.contribution_type)
    );
  }

  // Filter by search query — matches title or project name
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(
      (issue) =>
        issue.title.toLowerCase().includes(q) ||
        issue.project.name.toLowerCase().includes(q)
    );
  }

  const total = filtered.length;
  const start = (page - 1) * limit;
  const paginated = filtered.slice(start, start + limit);

  return {
    success: true,
    data: paginated,
    meta: { page, total, per_page: limit },
  };
}
