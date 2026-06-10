import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { motion, useReducedMotion } from "motion/react";
import { type ReactNode } from "react";

import { VectorDiamondIcon, WebDiamondIcon } from "@/components/icons";
import { type SourceFieldsFragment } from "@/graphql/generated";

/** Soft spring (DESIGN.md §2.5 --spring-soft). */
const SPRING_SOFT = { type: "spring", stiffness: 120, damping: 18, mass: 0.4 } as const;

function ChipShell({
  source,
  index,
  children,
}: {
  source: SourceFieldsFragment;
  index: number;
  children: ReactNode;
}) {
  const reducedMotion = useReducedMotion() ?? false;
  return (
    <motion.span
      className="inline-flex"
      initial={reducedMotion ? false : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ ...SPRING_SOFT, delay: reducedMotion ? 0 : index * 0.1 }}
      data-kind={source.kind}
    >
      {children}
    </motion.span>
  );
}

const CHIP_CLASS =
  "inline-flex min-h-11 items-center gap-1.5 rounded-sm border border-hairline bg-chip px-3 " +
  "font-mono text-meta text-text-dim transition-all duration-120 hover:-translate-y-0.5 " +
  "hover:border-azure/50 hover:text-text motion-reduce:hover:translate-y-0";

function ChipLabel({ source }: { source: SourceFieldsFragment }) {
  return (
    <>
      {source.kind === "VECTOR" ? (
        <VectorDiamondIcon className="h-3 w-3 shrink-0 text-azure" />
      ) : (
        <WebDiamondIcon className="h-3 w-3 shrink-0 text-azure-dim" />
      )}
      <span className="max-w-[18ch] truncate">{source.title}</span>
    </>
  );
}

/**
 * CitationChip (DESIGN.md §4.2): a retrieval source rendered as a chip —
 * ◆ filled = VECTOR, ◇ hollow = WEB. Appears BEFORE the answer completes
 * (SourcesResolved). WEB chips open the source in a new tab; VECTOR chips
 * reveal the matched snippet in a popover.
 */
export function CitationChip({ source, index }: { source: SourceFieldsFragment; index: number }) {
  const srLabel = `Source, ${source.kind === "VECTOR" ? "vector" : "web"}: ${source.title}${
    source.score != null ? `, relevance ${(source.score * 100).toFixed(0)} percent` : ""
  }`;

  if (source.kind === "WEB" && source.url != null) {
    return (
      <ChipShell source={source} index={index}>
        <a className={CHIP_CLASS} href={source.url} target="_blank" rel="noopener noreferrer">
          <span className="sr-only">{srLabel} (opens in a new tab)</span>
          <span aria-hidden className="inline-flex items-center gap-1.5">
            <ChipLabel source={source} />
          </span>
        </a>
      </ChipShell>
    );
  }

  return (
    <ChipShell source={source} index={index}>
      <TooltipPrimitive.Provider delayDuration={150}>
        <TooltipPrimitive.Root>
          <TooltipPrimitive.Trigger className={CHIP_CLASS}>
            <span className="sr-only">{srLabel}</span>
            <span aria-hidden className="inline-flex items-center gap-1.5">
              <ChipLabel source={source} />
            </span>
          </TooltipPrimitive.Trigger>
          <TooltipPrimitive.Portal>
            <TooltipPrimitive.Content
              sideOffset={6}
              className="z-50 max-w-72 rounded-md border border-hairline-2 bg-surface-2 px-3 py-2 text-meta leading-relaxed text-text"
            >
              {source.snippet ?? "No snippet recorded for this match."}
              {source.score != null ? (
                <span className="tabular mt-1 block font-mono text-micro text-text-dim">
                  score {source.score.toFixed(2)}
                </span>
              ) : null}
            </TooltipPrimitive.Content>
          </TooltipPrimitive.Portal>
        </TooltipPrimitive.Root>
      </TooltipPrimitive.Provider>
    </ChipShell>
  );
}
