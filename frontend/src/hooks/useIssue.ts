// useIssue.ts
// Custom hook for fetching a single issue with full project details.
// Used by the task detail page (/tasks/[id]).
// Data fetching is centralised in hooks — components never call the API directly.

import { useState, useEffect } from "react";
import { fetchIssue } from "@/lib/api";
import type { Issue, Project } from "@/lib/api";

export interface IssueDetail extends Issue {
  project: Project;
}

interface UseIssueResult {
  data: IssueDetail | null;
  isLoading: boolean;
  error: string | null;
  notFound: boolean;
}

/**
 * Fetches a single issue by UUID from GET /api/v1/issues/:id.
 *
 * Returns the full issue object with the complete project embedded —
 * so the detail page can render both the issue section and the
 * "About This Project" section without a second API call.
 *
 * @param id - UUID of the issue to fetch
 * @returns Object with data, isLoading, error, and notFound flag
 */
export function useIssue(id: string): UseIssueResult {
  const [data, setData] = useState<IssueDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      setNotFound(false);

      try {
        const result = await fetchIssue(id);
        if (!cancelled) {
          setData(result.data as IssueDetail);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        // 404 from the API means the issue doesn't exist or is inactive —
        // show a not-found state rather than a generic error.
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
          setNotFound(true);
        } else {
          console.error("Failed to fetch issue:", err);
          setError("Could not load this task. Please try again.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  return { data, isLoading, error, notFound };
}
