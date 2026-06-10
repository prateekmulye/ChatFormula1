import { CountdownHero } from "@/components/standings/countdown-hero";
import { Skeleton } from "@/components/ui/skeleton";
import { type RacesQuery, useNextRaceQuery, useRacesQuery } from "@/graphql/generated";
import { SEASON } from "@/lib/env";
import { cn } from "@/lib/utils";
import { DataError, PageHeading } from "@/routes/page-chrome";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

function RoundCard({ race, past }: { race: RacesQuery["races"][number]; past: boolean }) {
  return (
    <li
      className={cn(
        "relative overflow-hidden rounded-lg border border-hairline bg-surface-1 px-4 py-3",
        past && "opacity-60",
      )}
    >
      <span
        aria-hidden
        className="tabular pointer-events-none absolute -right-1 -top-3 font-mono text-numeral text-text-faint/20"
      >
        {String(race.round).padStart(2, "0")}
      </span>
      <p className="instrument text-micro text-text-faint">
        Round {race.round}
        {past ? " · finished" : ""}
      </p>
      <h3 className="mt-0.5 text-h3 font-semibold text-text">{race.name}</h3>
      <p className="text-meta text-text-dim">
        {race.circuit} · {race.country}
      </p>
      <p className="tabular mt-1 font-mono text-meta text-text-dim">
        {dateFormat.format(new Date(race.startsAt))}
      </p>
    </li>
  );
}

export function CalendarPage() {
  const nextRace = useNextRaceQuery();
  const races = useRacesQuery({ variables: { season: SEASON } });
  const now = Date.now();

  return (
    <div className="mx-auto max-w-[1200px] space-y-8 px-4 py-8">
      <PageHeading title={`${SEASON} Calendar`} kicker="Race weekends" />

      {nextRace.loading ? (
        <Skeleton className="h-44 w-full" />
      ) : (
        <CountdownHero race={nextRace.data?.nextRace ?? null} />
      )}

      {races.loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading calendar">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      ) : races.error !== undefined ? (
        <DataError
          message="The calendar query did not answer — the gateway may be cold-starting."
          onRetry={() => void races.refetch()}
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label={`${SEASON} rounds`}>
          {(races.data?.races ?? []).map((race) => (
            <RoundCard key={race.id} race={race} past={new Date(race.startsAt).getTime() < now} />
          ))}
        </ul>
      )}
    </div>
  );
}
