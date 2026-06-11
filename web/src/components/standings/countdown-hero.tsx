import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

import { type NextRaceQuery } from "@/graphql/generated";
import { cn } from "@/lib/utils";

type Race = NonNullable<NextRaceQuery["nextRace"]>;

interface Remaining {
  days: string;
  hours: string;
  minutes: string;
  seconds: string;
  totalMs: number;
}

function remainingUntil(startsAt: string, now: number): Remaining {
  const totalMs = Math.max(0, new Date(startsAt).getTime() - now);
  const totalSeconds = Math.floor(totalMs / 1000);
  const days = Math.floor(totalSeconds / 86_400);
  const hours = Math.floor((totalSeconds % 86_400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return { days: pad(days), hours: pad(hours), minutes: pad(minutes), seconds: pad(seconds), totalMs };
}

function DigitGroup({
  value,
  label,
  flip,
  compact,
}: {
  value: string;
  label: string;
  flip: boolean;
  compact: boolean;
}) {
  return (
    <span className="flex flex-col items-center">
      {/* Fixed-width digit slots: zero layout shift on tick (§3.3). */}
      <motion.span
        key={flip ? value : label}
        initial={flip ? { opacity: 0.2 } : false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.12 }}
        className={cn(
          "tabular font-mono text-text",
          compact ? "w-[2ch] text-h2" : "w-[2ch] text-numeral",
        )}
      >
        {value}
      </motion.span>
      <span className="instrument text-micro text-text-faint">{label}</span>
    </span>
  );
}

function CountdownDigits({ startsAt, compact }: { startsAt: string; compact: boolean }) {
  const reducedMotion = useReducedMotion() ?? false;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const remaining = remainingUntil(startsAt, now);

  // Coarse human label for SRs — the string only changes when a day/hour
  // flips, so the accessible name is not spammed every second (§6).
  const coarseLabel = `Next race in ${Number(remaining.days)} days, ${Number(remaining.hours)} hours`;

  const separator = <span className={cn("tabular font-mono text-text-faint", compact ? "text-h2" : "text-numeral")}>:</span>;

  return (
    <div aria-label={coarseLabel} role="timer">
      <div aria-hidden className="flex items-start gap-2 sm:gap-3">
        <DigitGroup value={remaining.days} label="DD" flip={false} compact={compact} />
        {separator}
        <DigitGroup value={remaining.hours} label="HH" flip={false} compact={compact} />
        {separator}
        <DigitGroup value={remaining.minutes} label="MM" flip={false} compact={compact} />
        {separator}
        <DigitGroup value={remaining.seconds} label="SS" flip={!reducedMotion} compact={compact} />
      </div>
    </div>
  );
}

/**
 * CountdownHero (DESIGN.md §4.2): next-race hero with big tabular numerals.
 * Country/circuit are plain text — no flags, no track logos (anti-slop 10).
 * `race === null` renders the honest no-upcoming-race state, never a fake
 * countdown (anti-slop 9).
 */
export function CountdownHero({ race, compact = false }: { race: Race | null; compact?: boolean }) {
  if (race === null) {
    return (
      <section
        className={cn(
          "rounded-xl border border-hairline bg-surface-1 px-6",
          compact ? "py-4" : "py-8",
        )}
      >
        <p className="instrument text-meta text-text-dim">Next race</p>
        <p className="mt-1 font-display text-h2 font-medium text-text">
          No upcoming race on the calendar
        </p>
        <p className="mt-1 text-meta text-text-dim">
          The seeded season has finished — the nightly standings sync (Phase 5) will load the next
          one.
        </p>
      </section>
    );
  }

  return (
    <section
      className={cn(
        "carbon-twill rounded-xl border border-hairline bg-surface-1 px-6",
        compact ? "py-4" : "py-8",
      )}
    >
      <p className="instrument text-meta text-azure">
        Next · Round {race.round} · {race.season}
      </p>
      <h2 className={cn("mt-1 font-display font-medium tracking-[-0.01em] text-text", compact ? "text-h3" : "text-h1")}>
        {race.name}
      </h2>
      <p className="mt-1 text-ui text-text-dim">
        {race.circuit} · {race.country}
      </p>
      <div className="mt-4">
        <CountdownDigits startsAt={race.startsAt} compact={compact} />
      </div>
    </section>
  );
}
