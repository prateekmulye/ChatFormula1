import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

import { PitRadioLog, type RadioLine } from "@/components/chat/pit-radio-log";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LIGHT_COUNT = 5;
/** Lights snap on left→right at 0.4s intervals (DESIGN.md §5.1 Ignition). */
const LIGHT_INTERVAL_S = 0.4;
const CLIMAX_S = 45;
const OVERRUN_S = 60;
const RETRY_S = 75;

const SCRIPT: ReadonlyArray<{ at: number; line: RadioLine }> = [
  { at: 0, line: { id: "l1", code: "0x01", text: "GATEWAY ONLINE", status: "ok" } },
  { at: 0.8, line: { id: "l2", code: "0x02", text: "WAKING INFERENCE ENGINE…", status: "busy" } },
  { at: 1.6, line: { id: "l3", code: "0x03", text: "COLD START · RENDER FREE TIER · ~45s", status: "info" } },
  { at: 12, line: { id: "l4", code: "0x04", text: "HYDRATING VECTOR INDEX…", status: "info" } },
  { at: 22, line: { id: "l5", code: "0x05", text: "COMPILING GRAPH…", status: "info" } },
  { at: 32, line: { id: "l6", code: "0x06", text: "NEGOTIATING UPSTREAM…", status: "info" } },
  { at: OVERRUN_S + 2, line: { id: "l8", code: "0x08", text: "RENDER FREE TIER · STILL SPOOLING", status: "busy" } },
];

const RESOLVED_LINE: RadioLine = { id: "l7", code: "0x07", text: "LIGHTS OUT · STREAMING", status: "ok" };

function Light({
  lit,
  resolved,
  overrun,
  climax,
  index,
  reducedMotion,
}: {
  lit: boolean;
  resolved: boolean;
  overrun: boolean;
  climax: boolean;
  index: number;
  reducedMotion: boolean;
}) {
  const color = resolved ? "bg-green" : overrun ? "bg-amber" : "bg-azure";
  const breathing =
    lit && !resolved && !reducedMotion
      ? {
          scale: [1, 1.06, 1],
          opacity: [0.85, 1, 0.85],
          transition: {
            duration: climax ? 1.0 : 2.8,
            repeat: Infinity,
            ease: "easeInOut" as const,
            delay: index * 0.1,
          },
        }
      : { scale: 1, opacity: resolved ? 0 : lit ? 1 : 1 };

  return (
    <motion.span
      initial={false}
      animate={breathing}
      className={cn(
        "h-5 w-5 rounded-full border sm:h-6 sm:w-6",
        lit ? cn(color, "border-transparent", !resolved && "glow-azure") : "border-hairline-2 bg-surface-3",
      )}
    />
  );
}

/**
 * LightsOutLoader (DESIGN.md §4.2, timing §5.1): the cold-start takeover.
 * Five gantry lights illuminate one by one; the PitRadioLog narrates with
 * honest free-tier copy. Overrun (>60s) turns the lights amber with
 * active-waiting copy — never "broken" — and surfaces a retry affordance at
 * ~75s. Resolution extinguishes all five, flashes green (Peak-End), and the
 * parent swaps in the streaming bubble.
 *
 * Reduced motion: no snaps/breathing/flash — static dots plus the log,
 * which carries the whole experience as text.
 */
export function LightsOutLoader({
  resolved,
  onRetry,
}: {
  /** Set when the first real pipeline event arrives — plays the resolution beat. */
  resolved: boolean;
  onRetry?: () => void;
}) {
  const reducedMotion = useReducedMotion() ?? false;
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 200);
    return () => window.clearInterval(interval);
  }, []);

  const litCount = resolved
    ? LIGHT_COUNT
    : Math.min(LIGHT_COUNT, Math.floor(elapsed / LIGHT_INTERVAL_S));
  const overrun = !resolved && elapsed >= OVERRUN_S;
  const climax = !resolved && elapsed >= CLIMAX_S && !overrun;

  const lines = SCRIPT.filter((entry) => entry.at <= elapsed).map((entry) => entry.line);
  if (resolved) lines.push(RESOLVED_LINE);

  // Goal-gradient progression: links 1→4 climb through the tension phase,
  // link 5 is reserved for the climax (§5.1 Zeigarnik beat).
  const linkNumber = Math.min(4, 1 + Math.floor(elapsed / (CLIMAX_S / 4)));
  const caption = resolved
    ? "Connected, response streaming."
    : overrun
      ? "Negotiating high-latency gateway · still spooling — free tier, not broken."
      : climax
        ? "Link 5 of 5 · almost green"
        : `Link ${linkNumber} of 5 · the wait is the demo`;

  return (
    <section
      aria-busy={!resolved}
      aria-label="Warming up the inference engine"
      className="flex flex-col items-center gap-6 py-10"
    >
      <h2 className="font-display text-h2 font-medium tracking-[-0.01em] text-text">
        Spooling up the engines
      </h2>

      <div aria-hidden className="flex flex-col items-center gap-2">
        <div className="flex gap-3 sm:gap-4">
          {Array.from({ length: LIGHT_COUNT }, (_, index) => (
            <Light
              key={index}
              index={index}
              lit={index < litCount || resolved}
              resolved={resolved}
              overrun={overrun}
              climax={climax}
              reducedMotion={reducedMotion}
            />
          ))}
        </div>
        <div className="h-px w-56 bg-hairline-2 sm:w-72" />
        {resolved && !reducedMotion ? (
          <motion.div
            className="h-1 w-56 rounded-full bg-green sm:w-72"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 0.4 }}
          />
        ) : null}
      </div>

      <PitRadioLog lines={lines} label="Pit radio — warm-up progress" />

      <p aria-live="polite" className="instrument text-meta text-text-dim">
        {caption}
      </p>

      {!resolved && elapsed >= RETRY_S && onRetry !== undefined ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Re-send the question
        </Button>
      ) : null}
    </section>
  );
}
