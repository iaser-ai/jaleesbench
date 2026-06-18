import { afterEach, describe, expect, it, vi } from "vitest";
import { applyTheme, getInitialTheme } from "./theme";

afterEach(() => {
  window.localStorage.clear();
  vi.unstubAllGlobals();
  document.documentElement.removeAttribute("data-theme");
});

function stubPrefersDark(matches: boolean) {
  vi.stubGlobal("matchMedia", (q: string) => ({ matches, media: q }));
}

describe("theme", () => {
  it("uses the persisted choice when present", () => {
  window.localStorage.setItem("theme", "dark");
    expect(getInitialTheme()).toBe("dark");
  });

  it("falls back to the OS preference when nothing is persisted", () => {
    stubPrefersDark(true);
    expect(getInitialTheme()).toBe("dark");
  window.localStorage.clear();
    stubPrefersDark(false);
    expect(getInitialTheme()).toBe("light");
  });

  it("defaults to light when matchMedia is unavailable (jsdom)", () => {
    // matchMedia is not stubbed → undefined → guarded → light, no crash.
    expect(getInitialTheme()).toBe("light");
  });

  it("applies data-theme to <html>", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
