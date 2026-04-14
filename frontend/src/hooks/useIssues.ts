// useIssues.ts
// Custom hook for fetching paginated issues from the Nocos API.
// Data fetching is centralised in hooks — components never fetch directly.
// Phase 1: Returns stub data. Will call real API in Phase 3.

import { useState, useEffect } from "react";
import { fetchIssues, type IssueListResponse } from "@/lib/api";

interface UseIssuesOptions {
  page?: number;
  limit?: number;
  type?: string;
  search?: string;
  paid?: boolean;
  difficulty?: string;
}

interface UseIssuesResult {
  data: IssueListResponse | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Fetches a paginated list of active issues from the Nocos backend.
 *
 * Supports filtering by contribution type, search query, paid status,
 * and difficulty. Returns loading and error states so components can
 * render appropriate UI for each state.
 *
 * @param options - Filter and pagination parameters
 * @returns Object with data, isLoading, and error
 */
export function useIssues(options: UseIssuesOptions = {}): UseIssuesResult {
  const { page = 1, limit = 12, type, search, paid, difficulty } = options;

  const [data, setData] = useState<IssueListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchIssues({ page, limit, type, search, paid, difficulty });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          // Log the error internally but show a safe message to the user
          console.error("Failed to fetch issues:", err);
          setError("Failed to load issues. Please try again.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    // Cleanup: if the component unmounts before the request resolves,
    // discard the result to prevent state updates on an unmounted component.
    return () => {
      cancelled = true;
    };
  }, [page, limit, type, search, paid, difficulty]);

  return { data, isLoading, error };
}
