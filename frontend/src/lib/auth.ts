/**
 * Token handling. The backend issues a short-lived bearer JWT (no cookies, no refresh token), so
 * the token must live in JavaScript. Trade-off, also documented in the README: it is kept in memory
 * and mirrored to sessionStorage (cleared when the tab closes; survives reloads). It is never put
 * in localStorage, never logged, and passwords are never stored.
 */
const STORAGE_KEY = 'novadocs.access_token';

let memoryToken: string | null = null;

export const tokenStore = {
  get(): string | null {
    if (memoryToken) return memoryToken;
    try {
      memoryToken = sessionStorage.getItem(STORAGE_KEY);
    } catch {
      memoryToken = null;
    }
    return memoryToken;
  },
  set(token: string): void {
    memoryToken = token;
    try {
      sessionStorage.setItem(STORAGE_KEY, token);
    } catch {
      /* storage unavailable: the in-memory token still works for this page load */
    }
  },
  clear(): void {
    memoryToken = null;
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  },
};

/**
 * Reads the `exp` claim (seconds since epoch) for UX only: scheduling the "session expired" flow.
 * The signature is NOT verified here; the backend is the only authority on token validity.
 */
export function getTokenExpiry(token: string): number | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    const exp = (JSON.parse(json) as { exp?: unknown }).exp;
    return typeof exp === 'number' ? exp : null;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string, skewSeconds = 5): boolean {
  const exp = getTokenExpiry(token);
  return exp !== null && exp * 1000 - skewSeconds * 1000 <= Date.now();
}
