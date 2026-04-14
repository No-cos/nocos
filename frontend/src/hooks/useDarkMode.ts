// useDarkMode.ts
// Custom hook for managing dark mode preference.
// Saves the user's preference to localStorage so it persists across sessions.
// Toggles the "dark" class on <html> — all color changes happen in CSS via variables.

import { useState, useEffect } from "react";

type Theme = "light" | "dark";

interface UseDarkModeResult {
  theme: Theme;
  toggleTheme: () => void;
}

/**
 * Manages the light/dark theme for the application.
 *
 * On first load, reads the saved preference from localStorage. If no
 * preference is saved, defaults to light mode. On toggle, updates both
 * the <html> class and localStorage.
 *
 * Components should never read theme directly — they use CSS variables
 * which respond automatically to the <html> class change.
 *
 * @returns Current theme and a toggle function
 */
export function useDarkMode(): UseDarkModeResult {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    // Read saved preference on mount — localStorage is only available in the browser.
    const saved = localStorage.getItem("nocos-theme") as Theme | null;
    const initial = saved ?? "dark";
    setTheme(initial);
    applyTheme(initial);
  }, []);

  function applyTheme(newTheme: Theme) {
    // Toggle "dark" class on <html> — CSS variables do the rest.
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    applyTheme(next);
    // Persist so the user doesn't lose their preference on page refresh
    localStorage.setItem("nocos-theme", next);
  }

  return { theme, toggleTheme };
}
