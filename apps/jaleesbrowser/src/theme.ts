import { useEffect, useState } from "react";
import { getStored, setStored } from "./storage";

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";

/** Persisted choice, else the OS preference, else light. (matchMedia is guarded
 *  so this is safe under jsdom / SSR.) */
export function getInitialTheme(): Theme {
  const saved = getStored(STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;
  const prefersDark =
    window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false;
  return prefersDark ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Theme state that applies `data-theme` on <html> and persists the choice. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  useEffect(() => {
    applyTheme(theme);
    setStored(STORAGE_KEY, theme);
  }, [theme]);
  return { theme, toggle: () => setTheme((t) => (t === "light" ? "dark" : "light")) };
}
