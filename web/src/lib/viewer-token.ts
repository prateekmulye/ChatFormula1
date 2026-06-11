/**
 * Anonymous viewer-token store.
 *
 * The gateway mints a signed Phoenix.Token per viewer. It arrives on HTTP
 * responses (echoed in the `x-viewer-token` header by the gateway's CORS
 * plug) and must be presented:
 *   - on HTTP requests as `Authorization: Bearer <token>`, and
 *   - on the graphql-ws handshake as `connectionParams: { token }`.
 *
 * The WS connection cannot open before a token exists, so the socket link
 * awaits `waitForViewerToken()` — the first HTTP response (systemHealth on
 * mount) resolves it.
 */
const STORAGE_KEY = "chatf1.viewer_token";

let token: string | null = readStoredToken();
const waiters: Array<(token: string) => void> = [];

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getViewerToken(): string | null {
  return token;
}

export function setViewerToken(next: string): void {
  if (next === token) return;
  token = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Private-mode storage failures are fine — the in-memory token still works.
  }
  while (waiters.length > 0) {
    waiters.shift()?.(next);
  }
}

export function waitForViewerToken(): Promise<string> {
  if (token !== null) return Promise.resolve(token);
  return new Promise((resolve) => {
    waiters.push(resolve);
  });
}
