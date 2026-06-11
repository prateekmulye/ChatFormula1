import { describe, expect, it } from "vitest";

import {
  type AgentStreamEvent,
  initialStreamState,
  reduceStreamEvent,
  type StreamState,
  streamText,
} from "@/features/chat/stream-reducer";
import { type MessageFieldsFragment } from "@/graphql/generated";

const MESSAGE_ID = "msg-1";

function token(seq: number, text: string): AgentStreamEvent {
  return { __typename: "TokenDelta", messageId: MESSAGE_ID, seq, text };
}

function node(nodeName: "WARMING_UP" | "ANALYZE_QUERY" | "GENERATE", startedAt: string): AgentStreamEvent {
  return { __typename: "NodeTransition", messageId: MESSAGE_ID, node: nodeName, startedAt };
}

function sources(): AgentStreamEvent {
  return {
    __typename: "SourcesResolved",
    messageId: MESSAGE_ID,
    sources: [{ kind: "VECTOR", title: "2026 regulations", url: null, snippet: null, score: 0.83 }],
  };
}

function completed(content: string): AgentStreamEvent {
  const message: MessageFieldsFragment = {
    id: MESSAGE_ID,
    role: "ASSISTANT",
    content,
    status: "COMPLETE",
    intent: null,
    cached: false,
    latencyMs: 312,
    insertedAt: "2026-06-10T00:00:00Z",
    sources: [],
  };
  return { __typename: "MessageCompleted", messageId: MESSAGE_ID, cached: false, message, usage: null };
}

function reduceAll(events: readonly AgentStreamEvent[], from: StreamState = initialStreamState) {
  return events.reduce(reduceStreamEvent, from);
}

describe("reduceStreamEvent — idempotency by seq", () => {
  it("drops an exact duplicate TokenDelta", () => {
    const state = reduceAll([node("ANALYZE_QUERY", "t0"), token(1, "Verst"), token(1, "Verst")]);
    expect(streamText(state)).toBe("Verst");
    expect(state.segments).toHaveLength(1);
    expect(state.gapDetected).toBe(false);
  });

  it("survives a full replay+live overlap without duplicating text", () => {
    // First delivery: node(seq 0), tokens 1..3.
    const live = [node("GENERATE", "t0"), token(1, "Lights "), token(2, "out "), token(3, "and ")];
    let state = reduceAll(live);
    // Reconnect: the gateway replays the buffer (same events, same seqs),
    // then live continues with seq 4.
    state = reduceAll([...live, token(4, "away")], state);
    expect(streamText(state)).toBe("Lights out and away");
    expect(state.segments.map((segment) => segment.seq)).toEqual([1, 2, 3, 4]);
    expect(state.gapDetected).toBe(false);
  });

  it("dedupes replayed NodeTransition and SourcesResolved by content key", () => {
    const events = [node("ANALYZE_QUERY", "t0"), sources(), node("ANALYZE_QUERY", "t0"), sources()];
    const state = reduceAll(events);
    expect(state.visitedNodes).toEqual(["ANALYZE_QUERY"]);
    expect(state.sources).toHaveLength(1);
  });
});

describe("reduceStreamEvent — gap detection", () => {
  it("flags a gap when a token seq skips with no interleaved events", () => {
    const state = reduceAll([node("GENERATE", "t0"), token(1, "a"), token(3, "c")]);
    expect(state.gapDetected).toBe(true);
  });

  it("does NOT flag a gap when the skip is explained by interleaved non-token events", () => {
    // Gateway seqs: node=0, token=1, sources=2, token=3 — only tokens carry seq.
    const state = reduceAll([
      node("ANALYZE_QUERY", "t0"),
      token(1, "Verstappen "),
      sources(),
      token(3, "leads"),
    ]);
    expect(state.gapDetected).toBe(false);
    expect(streamText(state)).toBe("Verstappen leads");
  });

  it("flags a gap when the first token seq exceeds the observed event count", () => {
    // Buffer truncated: we never saw seqs 0..4.
    const state = reduceAll([token(5, "…tail of an answer")]);
    expect(state.gapDetected).toBe(true);
  });

  it("keeps the flag once set (refetch is the only recovery)", () => {
    let state = reduceAll([token(2, "late")]);
    expect(state.gapDetected).toBe(true);
    state = reduceStreamEvent(state, token(3, " more"));
    expect(state.gapDetected).toBe(true);
  });
});

describe("reduceStreamEvent — batch ordering", () => {
  it("assembles text in seq order even when batches arrive out of order", () => {
    const state = reduceAll([node("GENERATE", "t0"), token(1, "A"), token(3, "C"), token(2, "B")]);
    expect(streamText(state)).toBe("ABC");
  });
});

describe("reduceStreamEvent — lifecycle", () => {
  it("maps WARMING_UP to the warming phase and GENERATE to streaming", () => {
    let state = reduceStreamEvent(initialStreamState, node("WARMING_UP", "t0"));
    expect(state.phase).toBe("warming");
    expect(state.currentNode).toBe("WARMING_UP");
    state = reduceStreamEvent(state, node("GENERATE", "t1"));
    expect(state.phase).toBe("streaming");
  });

  it("MessageCompleted finalizes: phase, authoritative content, idempotent", () => {
    let state = reduceAll([node("GENERATE", "t0"), token(1, "partial tex")]);
    state = reduceStreamEvent(state, completed("partial text, now complete"));
    expect(state.phase).toBe("complete");
    expect(streamText(state)).toBe("partial text, now complete");
    const again = reduceStreamEvent(state, completed("DIFFERENT"));
    expect(streamText(again)).toBe("partial text, now complete");
  });

  it("AgentError moves to failed and records retryability", () => {
    const state = reduceStreamEvent(initialStreamState, {
      __typename: "AgentError",
      messageId: MESSAGE_ID,
      code: "UPSTREAM_UNAVAILABLE",
      errorMessage: "agent unreachable",
      retryable: true,
    });
    expect(state.phase).toBe("failed");
    expect(state.error).toEqual({
      code: "UPSTREAM_UNAVAILABLE",
      message: "agent unreachable",
      retryable: true,
    });
  });
});
