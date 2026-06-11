import { motion, useReducedMotion } from "motion/react";
import { Fragment } from "react";

import { CitationChip } from "@/components/chat/citation-chip";
import { MessageBlocks } from "@/components/chat/message-blocks";
import { CautionTriangleIcon, ReplaySquareIcon, SignalDotIcon } from "@/components/icons";
import { humanizeStreamError } from "@/features/chat/error-copy";
import { type StreamState, streamText, type TokenSegment } from "@/features/chat/stream-reducer";
import { type SourceFieldsFragment } from "@/graphql/generated";

const SPRING_SIGNAL = { type: "spring", stiffness: 150, damping: 15, mass: 0.1 } as const;
const EASE_REVEAL = [0.16, 1, 0.3, 1] as const;

/** Assistant bubble: asymmetric corner anchors it to the left rail (§2.4). */
const BUBBLE_CLASS =
  "max-w-[65ch] rounded-[14px] rounded-bl-[4px] border border-hairline bg-surface-1 px-4 py-3 [contain:layout]";

function SourcesRow({ sources }: { sources: readonly SourceFieldsFragment[] }) {
  if (sources.length === 0) return null;
  return (
    <div data-testid="token-stream-sources" className="mb-2 flex flex-wrap gap-2">
      {sources.map((source, index) => (
        <CitationChip key={`${source.kind}:${source.title}`} source={source} index={index} />
      ))}
    </div>
  );
}

function FooterBadges({ latencyMs, cached }: { latencyMs: number | null; cached: boolean }) {
  return (
    <div
      data-testid="token-stream-footer"
      className="mt-2 flex items-center gap-3 border-t border-hairline pt-2"
    >
      {latencyMs != null ? (
        <span className="tabular font-mono text-micro text-text-dim">{latencyMs}&thinsp;ms</span>
      ) : null}
      {cached ? (
        <span className="instrument inline-flex items-center gap-1 text-micro text-amber">
          <ReplaySquareIcon className="h-3 w-3" /> cached
        </span>
      ) : (
        <span className="instrument inline-flex items-center gap-1 text-micro text-green">
          <SignalDotIcon className="h-2.5 w-2.5" /> live
        </span>
      )}
    </div>
  );
}

/**
 * One TokenDelta batch rendered as a word-group materialization
 * (DESIGN.md §5.2): the whole group rises together (opacity 0→1,
 * translateY(8px)→0, 200ms ease-reveal) — never a per-character typewriter.
 * Words are inline-block so transforms apply without breaking line wrap;
 * whitespace stays as plain text nodes so wrapping is unaffected.
 */
function WordGroup({ segment, animate }: { segment: TokenSegment; animate: boolean }) {
  const pieces = segment.text.split(/(\s+)/);
  return (
    <Fragment>
      {pieces.map((piece, index) => {
        if (piece.length === 0) return null;
        if (!animate || /^\s+$/.test(piece)) return <Fragment key={index}>{piece}</Fragment>;
        return (
          <motion.span
            key={index}
            className="inline-block"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: EASE_REVEAL }}
          >
            {piece}
          </motion.span>
        );
      })}
    </Fragment>
  );
}

/**
 * The Luminous Caret (DESIGN.md §4.2): 2px azure pill trailing the last
 * token; spring-pulses on each batch (keyed by the newest seq), oscillates
 * opacity during pauses. Removed on MessageCompleted. Decoration only.
 */
function LuminousCaret({ pulseKey, reducedMotion }: { pulseKey: number; reducedMotion: boolean }) {
  const baseClass = "ml-0.5 inline-block h-[1em] w-0.5 translate-y-[0.15em] rounded-full bg-azure";
  if (reducedMotion) return <span aria-hidden className={baseClass} />;
  return (
    <motion.span
      aria-hidden
      key={pulseKey}
      className={baseClass}
      initial={{ scaleY: 0.7 }}
      animate={{ scaleY: 1, opacity: [1, 0.4, 1] }}
      transition={{
        scaleY: SPRING_SIGNAL,
        opacity: { duration: 0.6, repeat: Infinity, ease: "easeInOut" },
      }}
    />
  );
}

/** A completed assistant message (also the refetched-after-gap path). */
export function AssistantMessage({
  content,
  sources,
  latencyMs,
  cached,
}: {
  content: string;
  sources: readonly SourceFieldsFragment[];
  latencyMs: number | null;
  cached: boolean;
}) {
  return (
    <div data-testid="token-stream" className={BUBBLE_CLASS}>
      <SourcesRow sources={sources} />
      <div data-testid="token-stream-body" className="text-body leading-[1.55] text-text">
        <MessageBlocks content={content} />
      </div>
      <FooterBadges latencyMs={latencyMs} cached={cached} />
    </div>
  );
}

/**
 * TokenStream — the streaming assistant bubble (DESIGN.md §4.2).
 *
 * Skeleton-first / zero-CLS: the bubble pre-allocates two text lines,
 * constrains to 65ch, and isolates layout (`contain: layout`). Citation
 * chips render ABOVE the answer as soon as SourcesResolved arrives — before
 * the text finishes. While streaming, raw text renders pre-wrap so structure
 * appears progressively; on completion it re-renders through the safe block
 * parser. Cache hits arrive as one synthesized TokenDelta and materialize as
 * a single group with the honest `cached` badge.
 */
export function TokenStream({ state }: { state: StreamState }) {
  const reducedMotion = useReducedMotion() ?? false;

  if (state.phase === "complete" && state.completion !== null) {
    return (
      <AssistantMessage
        content={streamText(state)}
        sources={state.sources ?? state.completion.message.sources}
        latencyMs={state.completion.message.latencyMs ?? null}
        cached={state.completion.cached}
      />
    );
  }

  const failed = state.phase === "failed";
  const newestSeq = state.segments[state.segments.length - 1]?.seq ?? -1;

  return (
    <div data-testid="token-stream" className={BUBBLE_CLASS}>
      <SourcesRow sources={state.sources ?? []} />
      <div
        data-testid="token-stream-body"
        aria-live="polite"
        aria-atomic="false"
        aria-busy={!failed}
        className="min-h-[3.1em] text-body leading-[1.55] text-text"
      >
        <p className="my-0 whitespace-pre-wrap">
          {state.segments.map((segment) => (
            <WordGroup
              key={segment.seq}
              segment={segment}
              animate={!reducedMotion && segment.seq === newestSeq}
            />
          ))}
          {!failed ? <LuminousCaret pulseKey={newestSeq} reducedMotion={reducedMotion} /> : null}
        </p>
        {failed && state.error !== null ? (
          <p className="mt-1 flex items-start gap-2 text-meta text-amber">
            <CautionTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" />
            {humanizeStreamError(state.error)}
          </p>
        ) : null}
      </div>
    </div>
  );
}
