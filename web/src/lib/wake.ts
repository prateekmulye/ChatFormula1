import { WAKE_URL } from "@/lib/env";

/**
 * Wake-on-paint (ARCHITECTURE §2): the first paint fires `GET /up` at the
 * gateway, whose warmup process pings the agent — Render's 30–60s cold start
 * burns while the visitor is still reading the hero copy.
 *
 * Fire-and-forget: an opaque no-cors fetch, errors swallowed. The UI never
 * depends on this response.
 */
export function fireWakePing(): void {
  void fetch(WAKE_URL, { mode: "no-cors", cache: "no-store", keepalive: true }).catch(
    () => undefined,
  );
}
