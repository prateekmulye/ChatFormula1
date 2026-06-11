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
import { type SystemStatsFieldsFragment, useSystemStatsQuery } from "@/graphql/generated";
import { cn } from "@/lib/utils";

/** Poll cadence while the ops panel is open (DESIGN.md §3.4). */
const POLL_INTERVAL_MS = 30_000;

/** Spend bar flips azure→amber once ≥80% of the daily budget is burned. */
const NEAR_CAP_FRACTION = 0.8;

function StatRow({ label, value }: { label: string; value: string }) {
  const missing = value === EM_DASH;
  return (
    <div className="flex items-center justify-between py-1.5">
      <dt className="instrument text-micro text-text-faint">{label}</dt>
      <dd
        className={cn("tabular font-mono text-meta", missing ? "text-text-faint" : "text-text")}
        aria-label={missing ? "not yet available" : undefined}
      >
        {value}
      </dd>
    </div>
  );
}

function SpendBar({ stats }: { stats: SystemStatsFieldsFragment }) {
  const fraction = spendFraction(stats.llmSpendTodayUsd, stats.dailyBudgetRemainingUsd);
  if (fraction === null) return null;
  const nearCap = fraction >= NEAR_CAP_FRACTION;
  return (
    <div
      data-testid="spend-bar"
      aria-hidden
      className="mb-1.5 h-1 w-full overflow-hidden rounded-full bg-surface-3"
    >
      <div
        data-testid="spend-bar-fill"
        className={cn("h-full rounded-full", nearCap ? "bg-amber" : "bg-azure")}
        style={{ width: `${Math.round(fraction * 100)}%` }}
      />
    </div>
  );
}

/**
 * Pure numerals block for the ops panel (DESIGN.md §3.4): big tabular mono
 * values, spend progress bar (azure→amber near cap), and em-dashes for any
 * value the gateway has not measured yet — never invented numbers.
 */
export function PitWallStats({ stats }: { stats: SystemStatsFieldsFragment | null }) {
  return (
    <div data-testid="pit-wall-stats">
      <dl>
        <StatRow
          label="ACTIVE CONVERSATIONS"
          value={stats ? formatCount(stats.activeConversations) : EM_DASH}
        />
        <StatRow
          label="BEAM PROCESSES"
          value={stats ? formatCount(stats.beamProcessCount) : EM_DASH}
        />
        <StatRow
          label="P95 FIRST TOKEN"
          value={stats ? formatFirstToken(stats.p95FirstTokenMs) : EM_DASH}
        />
        <StatRow
          label="THROUGHPUT"
          value={stats ? formatThroughput(stats.tokensPerSecond) : EM_DASH}
        />
        <StatRow label="UPTIME" value={stats ? formatUptime(stats.uptimeSeconds) : EM_DASH} />
      </dl>

      <div className="mt-1 border-t border-hairline pt-1">
        <dl>
          <StatRow
            label="LLM SPEND TODAY"
            value={
              stats
                ? `${formatUsd(stats.llmSpendTodayUsd)} / ${formatUsd(stats.dailyBudgetRemainingUsd)} remaining`
                : EM_DASH
            }
          />
        </dl>
        {stats !== null ? <SpendBar stats={stats} /> : null}
        <dl>
          <StatRow
            label="OBAN JOBS 24H"
            value={stats ? formatCount(stats.obanJobsCompleted24h) : EM_DASH}
          />
          <StatRow
            label="LAST SYNC"
            value={stats ? formatLastSync(stats.lastStandingsSyncAt) : EM_DASH}
          />
        </dl>
      </div>
    </div>
  );
}

/**
 * systemStats wiring for the panel. Lives INSIDE the sheet content, which
 * Radix unmounts when the panel closes — so the 30s poll runs only while
 * the panel is open, with zero background polling.
 */
export function LiveTelemetry() {
  const { data, error } = useSystemStatsQuery({
    pollInterval: POLL_INTERVAL_MS,
    fetchPolicy: "cache-and-network",
    nextFetchPolicy: "cache-and-network",
  });
  const stats = data?.systemStats ?? null;

  return (
    <>
      <PitWallStats stats={stats} />
      {error !== undefined && stats === null ? (
        <p className="mt-2 text-micro leading-relaxed text-text-dim">
          The gateway did not answer the <code className="font-mono">systemStats</code> query —
          numerals stay withheld rather than invented.
        </p>
      ) : null}
    </>
  );
}
