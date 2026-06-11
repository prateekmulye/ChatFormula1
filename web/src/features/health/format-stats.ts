/**
 * Pure formatters for the PitWallPanel telemetry numerals (DESIGN.md §3.4).
 *
 * Honesty contract (anti-slop rule 9): a missing value renders as an
 * em-dash — never an invented number, never a zero standing in for unknown.
 */

export const EM_DASH = "—";

/** Locale-grouped integer: 4318 → "4,318". */
export function formatCount(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

/** Gateway uptime as "6d 14:22:08" (hours-only spans drop the day part). */
export function formatUptime(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(clamped / 86_400);
  const hms = [
    Math.floor((clamped % 86_400) / 3_600),
    Math.floor((clamped % 3_600) / 60),
    clamped % 60,
  ]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
  return days > 0 ? `${days}d ${hms}` : hms;
}

/** p95 first-token latency; null until at least one stream completes. */
export function formatFirstToken(ms: number | null | undefined): string {
  return ms == null ? EM_DASH : `${formatCount(ms)} ms`;
}

/** Mean stream throughput; null until at least one stream completes. */
export function formatThroughput(tokensPerSecond: number | null | undefined): string {
  return tokensPerSecond == null ? EM_DASH : `${tokensPerSecond.toFixed(1)} tok/s`;
}

export function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`;
}

/** Coarse "2h ago" style relative time for the last standings sync. */
export function formatLastSync(iso: string | null | undefined, now: Date = new Date()): string {
  if (iso == null) return EM_DASH;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return EM_DASH;
  const minutes = Math.max(0, Math.floor((now.getTime() - then) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Fraction of today's LLM budget already spent (0–1), derived from the two
 * telemetry-fed fields (cap = spend + remaining). Null when the cap is zero
 * — no bar is drawn rather than faking a full or empty one.
 */
export function spendFraction(spendUsd: number, remainingUsd: number): number | null {
  const cap = spendUsd + remainingUsd;
  if (cap <= 0) return null;
  return Math.min(1, Math.max(0, spendUsd / cap));
}
