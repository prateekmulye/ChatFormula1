import { motion, useReducedMotion } from "motion/react";

import { CheckIcon, HollowCircleIcon, LoopIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

export interface RadioLine {
  readonly id: string;
  /** Hex-style line code, e.g. "0x03". */
  readonly code: string;
  readonly text: string;
  readonly status: "ok" | "busy" | "info";
}

const STATUS_VISUAL = {
  ok: { Icon: CheckIcon, className: "text-green" },
  busy: { Icon: LoopIcon, className: "text-amber" },
  info: { Icon: HollowCircleIcon, className: "text-azure" },
} as const;

/**
 * PitRadioLog (DESIGN.md §4.2): the mono aria-live log spine used inside the
 * LightsOutLoader. Each line: `0x__  MESSAGE  status-glyph`; lines enter
 * translateY(8px)→0. This text IS the accessible narration of the loader.
 */
export function PitRadioLog({ lines, label }: { lines: readonly RadioLine[]; label: string }) {
  const reducedMotion = useReducedMotion() ?? false;
  return (
    <div
      role="log"
      aria-live="polite"
      aria-label={label}
      className="w-full max-w-xl rounded-md border border-hairline bg-surface-1 px-4 py-3"
    >
      <p className="instrument mb-2 text-micro text-text-faint">Pit radio</p>
      <ol className="space-y-1.5">
        {lines.map((line) => {
          const { Icon, className } = STATUS_VISUAL[line.status];
          return (
            <motion.li
              key={line.id}
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="flex items-baseline gap-3 font-mono text-meta"
            >
              <span className="tabular text-text-faint">{line.code}</span>
              <span className="instrument flex-1 text-text-dim">{line.text}</span>
              <Icon className={cn("h-3.5 w-3.5 shrink-0 self-center", className)} />
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}
