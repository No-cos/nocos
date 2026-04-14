// api.ts
// Typed fetch wrapper for the Nocos backend API.
// All API calls go through this module — never use raw fetch in components.
// The base URL is pulled from the NEXT_PUBLIC_API_URL env variable so
// that local development and production use different endpoints automatically.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Type Definitions ──────────────────────────────────────────────────────────

export interface SocialLinks {
  twitter: string | null;
  discord: string | null;
  slack: string | null;
  linkedin: string | null;
  youtube: string | null;
  github: string;
}

export interface Project {
  id: string;
  name: string;
  github_url: string;
  github_owner: string;
  github_repo: string;
  description: string;
  website_url: string | null;
  avatar_url: string;
  social_links: SocialLinks;
  activity_score: number;
  activity_status: "active" | "slow" | "inactive";
  last_commit_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: string;
  project_id: string;
  project: Pick<Project, "name" | "avatar_url" | "activity_status">;
  title: string;
  description_display: string;
  is_ai_generated: boolean;
  labels: string[];
  contribution_type: string;
  is_paid: boolean;
  difficulty: "beginner" | "intermediate" | "advanced" | null;
  source: "github_scrape" | "manual_post";
  github_issue_url: string;
  github_created_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IssueListResponse {
  success: boolean;
  data: Issue[];
  meta: {
    page: number;
    total: number;
    per_page: number;
  };
}

export interface IssueDetailResponse {
  success: boolean;
  data: Issue & { project: Project };
}

export interface ApiError {
  success: false;
  error: string;
  code: string;
}

// ─── Fetch Helpers ─────────────────────────────────────────────────────────────

/**
 * Internal helper that wraps fetch with error handling and JSON parsing.
 * Throws on non-2xx responses so callers can handle errors uniformly.
 */
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  const json = await response.json();

  if (!response.ok) {
    const err = json as ApiError;
    throw new Error(err.error ?? `HTTP ${response.status}`);
  }

  return json as T;
}

// ─── Public API Functions ──────────────────────────────────────────────────────

interface FetchIssuesOptions {
  page?: number;
  limit?: number;
  type?: string;
  search?: string;
  paid?: boolean;
  difficulty?: string;
}

/**
 * Fetch a paginated list of active issues with optional filters.
 * Maps directly to GET /api/v1/issues.
 */
export async function fetchIssues(
  options: FetchIssuesOptions = {}
): Promise<IssueListResponse> {
  const params = new URLSearchParams();

  if (options.page) params.set("page", String(options.page));
  if (options.limit) params.set("limit", String(options.limit));
  if (options.type) params.set("type", options.type);
  if (options.search) params.set("search", options.search);
  if (options.paid !== undefined) params.set("paid", String(options.paid));
  if (options.difficulty) params.set("difficulty", options.difficulty);

  const query = params.toString();
  return apiFetch<IssueListResponse>(`/api/v1/issues${query ? `?${query}` : ""}`);
}

/**
 * Fetch a single issue with full project details.
 * Maps directly to GET /api/v1/issues/:id.
 */
export async function fetchIssue(id: string): Promise<IssueDetailResponse> {
  return apiFetch<IssueDetailResponse>(`/api/v1/issues/${id}`);
}

/**
 * Fetch a single project's details including social links and activity.
 * Maps directly to GET /api/v1/projects/:id.
 */
export async function fetchProject(id: string): Promise<Project> {
  const response = await apiFetch<{ success: boolean; data: Project }>(
    `/api/v1/projects/${id}`
  );
  return response.data;
}

/**
 * Subscribe an email address to the weekly digest.
 * Maps directly to POST /api/v1/subscribe.
 */
export async function subscribeEmail(
  email: string,
  tagPreferences: string[] = []
): Promise<{ success: boolean; message: string }> {
  return apiFetch("/api/v1/subscribe", {
    method: "POST",
    body: JSON.stringify({ email, tag_preferences: tagPreferences }),
  });
}
