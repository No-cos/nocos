// useProject.ts
// Custom hook for fetching a single project's details from the Nocos API.
// Used on the task detail page for the "About This Project" section.

import { useState, useEffect } from "react";
import { fetchProject, type Project } from "@/lib/api";

interface UseProjectResult {
  data: Project | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Fetches project details by ID from the Nocos backend.
 *
 * Returns the project's name, description, avatar, social links, and
 * activity status. If the project is not found, error is set and data
 * remains null.
 *
 * @param projectId - The UUID of the project to fetch
 * @returns Object with data, isLoading, and error
 */
export function useProject(projectId: string): UseProjectResult {
  const [data, setData] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;

    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchProject(projectId);
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to fetch project:", err);
          setError("Failed to load project details.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return { data, isLoading, error };
}
