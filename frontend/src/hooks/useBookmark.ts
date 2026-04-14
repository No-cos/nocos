// useBookmark.ts
// Hook for saving/removing issue bookmarks in localStorage.
// No auth is required in v1 — bookmarks are browser-local only.
// The bookmark state persists across page refreshes.

import { useState, useEffect } from "react";

const STORAGE_KEY = "nocos:bookmarks";

/**
 * Manages a single issue's bookmark state in localStorage.
 *
 * Reads initial state from localStorage on mount so bookmarks survive
 * page refreshes. Toggling writes the full bookmarks array back so all
 * bookmarked issues remain accessible from a future bookmarks page.
 *
 * @param issueId - UUID of the issue to bookmark
 * @returns Object with isBookmarked flag and toggle function
 */
export function useBookmark(issueId: string) {
  const [isBookmarked, setIsBookmarked] = useState(false);

  // Read from localStorage on mount — it's only available in the browser
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const bookmarks: string[] = stored ? JSON.parse(stored) : [];
      setIsBookmarked(bookmarks.includes(issueId));
    } catch {
      // Corrupt storage — start fresh rather than crashing
      setIsBookmarked(false);
    }
  }, [issueId]);

  function toggle() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const bookmarks: string[] = stored ? JSON.parse(stored) : [];
      let next: string[];

      if (bookmarks.includes(issueId)) {
        next = bookmarks.filter((id) => id !== issueId);
      } else {
        next = [...bookmarks, issueId];
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setIsBookmarked(next.includes(issueId));
    } catch {
      // localStorage may be unavailable (private browsing, quota exceeded)
      // Silently update local state so the UI still responds
      setIsBookmarked((prev) => !prev);
    }
  }

  return { isBookmarked, toggle };
}
