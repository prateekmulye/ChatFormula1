import {
  type AgentNode,
  type AgentStreamSubscription,
  type ErrorCode,
  type MessageFieldsFragment,
  type SourceFieldsFragment,
} from "@/graphql/generated";

/** One member of the AgentEvent union as delivered by the subscription. */
export type AgentStreamEvent = NonNullable<AgentStreamSubscription["agentStream"]>;

export type StreamPhase =
  | "idle"
  | "warming"
  | "streaming"
  | "replaying"
  | "complete"
  | "failed";

export interface TokenSegment {
  readonly seq: number;
  readonly text: string;
}

export interface StreamError {
  readonly code: ErrorCode;
  readonly message: string;
  readonly retryable: boolean;
}

export interface StreamCompletion {
  readonly message: MessageFieldsFragment;
  readonly cached: boolean;
}

export interface StreamState {
  readonly phase: StreamPhase;
  /** Accepted token batches, kept sorted by seq. */
  readonly segments: readonly TokenSegment[];
  /** Highest accepted TokenDelta seq (-1 before the first batch). */
  readonly maxTokenSeq: number;
  /**
   * Non-token events accepted since the last token batch. Every buffered
   * event consumes one gateway seq but only TokenDelta exposes its seq, so
   * this credit keeps interleaved NodeTransition/SourcesResolved events from
   * reading as token gaps.
   */
  readonly seqCredit: number;
  /** Dedupe keys for non-token events (replay + live overlap delivers duplicates). */
  readonly seenEventKeys: ReadonlySet<string>;
  readonly currentNode: AgentNode | null;
  readonly visitedNodes: readonly AgentNode[];
  readonly sources: readonly SourceFieldsFragment[] | null;
  readonly completion: StreamCompletion | null;
  readonly error: StreamError | null;
  /**
   * True once a TokenDelta seq jumped past what replay could explain — the
   * consumer must refetch the message from Postgres (always authoritative).
   */
  readonly gapDetected: boolean;
}

export const initialStreamState: StreamState = {
  phase: "idle",
  segments: [],
  maxTokenSeq: -1,
  seqCredit: 0,
  seenEventKeys: new Set(),
  currentNode: null,
  visitedNodes: [],
  sources: null,
  completion: null,
  error: null,
  gapDetected: false,
};

/** Full streamed text. The completed message content is authoritative. */
export function streamText(state: StreamState): string {
  if (state.completion !== null) return state.completion.message.content;
  return state.segments.map((segment) => segment.text).join("");
}

function withSeenKey(state: StreamState, key: string): ReadonlySet<string> {
  const next = new Set(state.seenEventKeys);
  next.add(key);
  return next;
}

function insertSorted(
  segments: readonly TokenSegment[],
  segment: TokenSegment,
): readonly TokenSegment[] {
  // Ordered transport makes appends the common case; splice covers replays.
  const last = segments[segments.length - 1];
  if (last === undefined || last.seq < segment.seq) return [...segments, segment];
  const index = segments.findIndex((existing) => existing.seq > segment.seq);
  return [...segments.slice(0, index), segment, ...segments.slice(index)];
}

function reduceTokenDelta(
  state: StreamState,
  event: Extract<AgentStreamEvent, { __typename: "TokenDelta" }>,
): StreamState {
  // Idempotency: replay-then-live overlap re-delivers batches; drop by seq.
  if (state.segments.some((segment) => segment.seq === event.seq)) return state;

  // Gap check: the next token seq may exceed maxTokenSeq + 1 only by the
  // number of interleaved non-token events we actually saw (the credit).
  const expectedCeiling = state.maxTokenSeq + 1 + state.seqCredit;
  const gapDetected = state.gapDetected || event.seq > expectedCeiling;

  return {
    ...state,
    phase: state.phase === "replaying" ? "replaying" : "streaming",
    segments: insertSorted(state.segments, { seq: event.seq, text: event.text }),
    maxTokenSeq: Math.max(state.maxTokenSeq, event.seq),
    seqCredit: 0,
    gapDetected,
  };
}

function reduceNodeTransition(
  state: StreamState,
  event: Extract<AgentStreamEvent, { __typename: "NodeTransition" }>,
): StreamState {
  const key = `node:${event.node}:${event.startedAt}`;
  if (state.seenEventKeys.has(key)) return state;

  const phase: StreamPhase =
    event.node === "WARMING_UP"
      ? "warming"
      : event.node === "REPLAYING_CACHE"
        ? "replaying"
        : "streaming";

  const visitedNodes =
    state.visitedNodes[state.visitedNodes.length - 1] === event.node
      ? state.visitedNodes
      : [...state.visitedNodes, event.node];

  return {
    ...state,
    phase,
    seqCredit: state.seqCredit + 1,
    seenEventKeys: withSeenKey(state, key),
    currentNode: event.node,
    visitedNodes,
  };
}

function reduceSourcesResolved(
  state: StreamState,
  event: Extract<AgentStreamEvent, { __typename: "SourcesResolved" }>,
): StreamState {
  const key = `sources:${event.sources.map((source) => `${source.kind}|${source.title}`).join(";")}`;
  if (state.seenEventKeys.has(key)) return state;

  return {
    ...state,
    seqCredit: state.seqCredit + 1,
    seenEventKeys: withSeenKey(state, key),
    sources: event.sources,
  };
}

function reduceMessageCompleted(
  state: StreamState,
  event: Extract<AgentStreamEvent, { __typename: "MessageCompleted" }>,
): StreamState {
  if (state.completion !== null) return state;
  return {
    ...state,
    phase: "complete",
    completion: { message: event.message, cached: event.cached },
    sources: state.sources ?? event.message.sources,
    currentNode: null,
  };
}

function reduceAgentError(
  state: StreamState,
  event: Extract<AgentStreamEvent, { __typename: "AgentError" }>,
): StreamState {
  if (state.error !== null) return state;
  return {
    ...state,
    phase: "failed",
    error: { code: event.code, message: event.errorMessage, retryable: event.retryable },
    currentNode: null,
  };
}

/**
 * Pure, idempotent reducer for the agentStream AgentEvent union.
 *
 * Reliability semantics (ARCHITECTURE §4.5): on reconnect the gateway replays
 * buffered events BEFORE live publishing resumes, so duplicates are expected
 * and ordering is per-connection. TokenDelta dedupes by seq; other events
 * dedupe by content key. A seq jump that replay cannot explain sets
 * `gapDetected` — the consumer refetches from Postgres.
 */
export function reduceStreamEvent(state: StreamState, event: AgentStreamEvent): StreamState {
  switch (event.__typename) {
    case "TokenDelta":
      return reduceTokenDelta(state, event);
    case "NodeTransition":
      return reduceNodeTransition(state, event);
    case "SourcesResolved":
      return reduceSourcesResolved(state, event);
    case "MessageCompleted":
      return reduceMessageCompleted(state, event);
    case "AgentError":
      return reduceAgentError(state, event);
  }
}
