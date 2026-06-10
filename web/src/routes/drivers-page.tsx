import { Skeleton } from "@/components/ui/skeleton";
import { type DriversQuery, useDriversQuery } from "@/graphql/generated";
import { SEASON } from "@/lib/env";
import { DataError, PageHeading } from "@/routes/page-chrome";

type Driver = NonNullable<DriversQuery["drivers"]>[number];

/** Driver card: oversized ghost mono numeral behind name + code (§3.3). */
function DriverCard({ driver }: { driver: Driver }) {
  return (
    <li className="relative overflow-hidden rounded-lg border border-hairline bg-surface-1 px-4 py-4">
      <span
        aria-hidden
        className="tabular pointer-events-none absolute -right-2 -top-6 font-mono text-numeral text-text-faint/20"
      >
        {driver.number ?? "—"}
      </span>
      <p className="instrument text-micro text-azure">{driver.code}</p>
      <h3 className="mt-0.5 text-h3 font-semibold text-text">{driver.fullName}</h3>
      <p className="text-meta text-text-dim">{driver.constructor.name}</p>
      <p className="mt-1 text-micro text-text-faint">{driver.nationality}</p>
    </li>
  );
}

export function DriversPage() {
  const { data, loading, error, refetch } = useDriversQuery({ variables: { season: SEASON } });

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <PageHeading title={`${SEASON} Drivers`} kicker="The grid" />
      {loading ? (
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-busy="true" aria-label="Loading drivers">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : error !== undefined ? (
        <DataError
          message="The drivers query did not answer — the gateway may be cold-starting."
          onRetry={() => void refetch()}
        />
      ) : (
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Drivers">
          {(data?.drivers ?? []).map((driver) => (
            <DriverCard key={driver.id} driver={driver} />
          ))}
        </ul>
      )}
    </div>
  );
}
