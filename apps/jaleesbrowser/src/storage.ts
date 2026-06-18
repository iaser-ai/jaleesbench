/**
 * localStorage access that degrades gracefully when storage is unavailable or
 * blocked (private mode, disabled cookies, SSR) — never throws.
 */

export function getStored(key: string): string | null {
  try {
    return window.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function setStored(key: string, value: string): void {
  try {
    window.localStorage?.setItem(key, value);
  } catch {
    /* ignore — storage unavailable */
  }
}
