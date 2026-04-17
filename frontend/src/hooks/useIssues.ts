/**
 * useIssues.ts
 *
 * Custom hook for fetching paginated issues from the Nocos API.
 * Data fetching is centralised here — components never fetch directly.
 *
 * Development fallback: if the backend is not running locally, the hook
 * automatically falls back to mock data so the UI can be previewed without
 * a running backend. Mock data is never used in production.
 */

import { useState, useEffect } from "react";
import { fetchIssues, type IssueListResponse } from "@/lib/api";
import { getMockIssues } from "@/lib/mock-data";

const IS_DEV = process.env.NODE_ENV === "development";

interface UseIssuesOptions {
  page?: number;
  limit?: number;
  types?: string;
  type?: string;
  search?: string;
  paid?: boolean;
  bounty?: boolean;
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
 * In development, if the API call fails (e.g. backend not running),
 * it silently falls back to mock data so the UI remains previewable.
 *
 * In production, a failed API call surfaces a user-facing error message.
 *
 * @param options - Filter and pagination parameters
 * @returns Object with data, isLoading, and error
 */
export function useIssues(options: UseIssuesOptions = {}): UseIssuesResult {
  const { page = 1, limit = 12, types, type, search, paid, bounty, difficulty } = options;

  const [data, setData] = useState<IssueListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchIssues({ page, limit, types, type, search, paid, bounty, difficulty });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (cancelled) return;

        if (IS_DEV) {
          // Backend not running — fall back to mock data silently in development.
          // This lets the UI be previewed without a running backend.
          console.warn(
            "[Nocos dev] Backend unavailable — using mock data. Start the backend to use real data:\n  cd backend && uvicorn main:app --reload"
          );
          setData(getMockIssues({ page, limit, types, type, search }));
        } else {
          // In production, always surface the error to the user.
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

    // Cleanup: discard the result if the component unmounts before
    // the request resolves, to prevent state updates on unmounted components.
    return () => {
      cancelled = true;
    };
  }, [page, limit, types, type, search, paid, bounty, difficulty]);

  return { data, isLoading, error };
}
