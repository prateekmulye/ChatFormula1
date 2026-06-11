import { describe, expect, it } from "vitest";

import {
  EM_DASH,
  formatCount,
  formatFirstToken,
  formatLastSync,
  formatThroughput,
  formatUptime,
  formatUsd,
  spendFraction,
} from "@/features/health/format-stats";

describe("format-stats", () => {
  it("groups counts with locale separators", () => {
    expect(formatCount(4318)).toBe("4,318");
    expect(formatCount(0)).toBe("0");
  });

  it("formats uptime as Dd HH:MM:SS, dropping the day part under 24h", () => {
    expect(formatUptime(6 * 86_400 + 14 * 3_600 + 22 * 60 + 8)).toBe("6d 14:22:08");
    expect(formatUptime(3_600 + 5)).toBe("01:00:05");
    expect(formatUptime(0)).toBe("00:00:00");
  });

  it("renders null latency and throughput as em-dash — never invented numbers", () => {
    expect(formatFirstToken(null)).toBe(EM_DASH);
    expect(formatFirstToken(undefined)).toBe(EM_DASH);
    expect(formatFirstToken(312)).toBe("312 ms");
    expect(formatThroughput(null)).toBe(EM_DASH);
    expect(formatThroughput(48.23)).toBe("48.2 tok/s");
  });

  it("formats USD to cents", () => {
    expect(formatUsd(0.42)).toBe("$0.42");
    expect(formatUsd(2)).toBe("$2.00");
  });

  it("renders last sync as coarse relative time, em-dash when never synced", () => {
    const now = new Date("2026-06-10T12:00:00Z");
    expect(formatLastSync(null, now)).toBe(EM_DASH);
    expect(formatLastSync("not-a-date", now)).toBe(EM_DASH);
    expect(formatLastSync("2026-06-10T11:59:40Z", now)).toBe("just now");
    expect(formatLastSync("2026-06-10T11:15:00Z", now)).toBe("45m ago");
    expect(formatLastSync("2026-06-10T10:00:00Z", now)).toBe("2h ago");
    expect(formatLastSync("2026-06-07T12:00:00Z", now)).toBe("3d ago");
  });

  it("derives the spend fraction from spend + remaining, clamped to 0–1", () => {
    expect(spendFraction(0.42, 1.58)).toBeCloseTo(0.21);
    expect(spendFraction(2, 0)).toBe(1);
    expect(spendFraction(0, 2)).toBe(0);
    // Zero cap → no bar instead of a fake one.
    expect(spendFraction(0, 0)).toBeNull();
  });
});
