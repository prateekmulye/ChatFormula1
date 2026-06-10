import { StandingsTable } from "@/components/standings/standings-table";
import { DataError, PageHeading } from "@/routes/page-chrome";
import { Skeleton } from "@/components/ui/skeleton";
import { useStandingsQuery } from "@/graphql/generated";
import { SEASON } from "@/lib/env";

export function StandingsPage() {
  const { data, loading, error, refetch } = useStandingsQuery({ variables: { season: SEASON } });

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <PageHeading title={`${SEASON} Drivers' Standings`} kicker="Championship" />
      {loading ? (
        <div className="mt-6 space-y-2" aria-busy="true" aria-label="Loading standings">
          {Array.from({ length: 10 }, (_, index) => (
            <Skeleton key={index} className="h-11 w-full" />
          ))}
        </div>
      ) : error !== undefined ? (
        <DataError
          message="The standings query did not answer — the gateway may be cold-starting."
          onRetry={() => void refetch()}
        />
      ) : (data?.standings ?? []).length === 0 ? (
        <div className="mt-6 rounded-lg border border-hairline bg-surface-1 px-5 py-6">
          <p className="instrument text-meta text-text-dim">No race results recorded yet</p>
          <p className="mt-1 max-w-[55ch] text-meta leading-relaxed text-text-faint">
            Standings aggregate from race results, and the nightly Jolpica results sync ships in
            Phase 5 — this table fills itself the first night it runs.
          </p>
        </div>
      ) : (
        <div className="mt-6">
          <StandingsTable rows={data?.standings ?? []} season={SEASON} />
        </div>
      )}
    </div>
  );
}
