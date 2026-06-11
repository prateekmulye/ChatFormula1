import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PitWallStats } from "@/components/telemetry/pit-wall-stats";
import { type SystemStatsFieldsFragment } from "@/graphql/generated";

const FULL_STATS: SystemStatsFieldsFragment = {
  activeConversations: 12,
  beamProcessCount: 4318,
  uptimeSeconds: 6 * 86_400 + 14 * 3_600 + 22 * 60 + 8,
  p95FirstTokenMs: 312,
  tokensPerSecond: 48.2,
  obanJobsCompleted24h: 37,
  lastStandingsSyncAt: new Date(Date.now() - 2 * 3_600_000).toISOString(),
  llmSpendTodayUsd: 0.42,
  dailyBudgetRemainingUsd: 1.58,
};

function statValues(): string[] {
  const block = screen.getByTestId("pit-wall-stats");
  return within(block)
    .getAllByRole("definition")
    .map((dd) => dd.textContent ?? "");
}

describe("PitWallStats", () => {
  it("renders every slot as an em-dash before the first stats response", () => {
    render(<PitWallStats stats={null} />);
    const values = statValues();
    expect(values).toHaveLength(8);
    expect(values.every((value) => value === "—")).toBe(true);
    // No bar without real numbers — nothing invented.
    expect(screen.queryByTestId("spend-bar")).not.toBeInTheDocument();
  });

  it("renders nullable telemetry fields as em-dash inside a real snapshot", () => {
    render(
      <PitWallStats
        stats={{
          ...FULL_STATS,
          p95FirstTokenMs: null,
          tokensPerSecond: null,
          lastStandingsSyncAt: null,
        }}
      />,
    );
    const values = statValues();
    expect(values.filter((value) => value === "—")).toHaveLength(3);
    // The non-null numerals still render honestly.
    expect(values).toContain("12");
    expect(values).toContain("4,318");
  });

  it("formats the measured numerals per the design spec", () => {
    render(<PitWallStats stats={FULL_STATS} />);
    const values = statValues();
    expect(values).toContain("312 ms");
    expect(values).toContain("48.2 tok/s");
    expect(values).toContain("6d 14:22:08");
    expect(values).toContain("$0.42 / $1.58 remaining");
    expect(values).toContain("2h ago");
  });

  it("draws the spend bar in azure when comfortably under the cap", () => {
    render(<PitWallStats stats={FULL_STATS} />);
    const fill = screen.getByTestId("spend-bar-fill");
    expect(fill.className).toContain("bg-azure");
    expect(fill.style.width).toBe("21%");
  });

  it("flips the spend bar to amber near the cap", () => {
    render(
      <PitWallStats
        stats={{ ...FULL_STATS, llmSpendTodayUsd: 1.8, dailyBudgetRemainingUsd: 0.2 }}
      />,
    );
    const fill = screen.getByTestId("spend-bar-fill");
    expect(fill.className).toContain("bg-amber");
    expect(fill.style.width).toBe("90%");
  });
});
