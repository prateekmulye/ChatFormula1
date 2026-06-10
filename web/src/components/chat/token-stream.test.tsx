import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TokenStream } from "@/components/chat/token-stream";
import { initialStreamState, type StreamState } from "@/features/chat/stream-reducer";

function streamingState(overrides: Partial<StreamState> = {}): StreamState {
  return {
    ...initialStreamState,
    phase: "streaming",
    segments: [
      { seq: 1, text: "Verstappen leads " },
      { seq: 2, text: "with 312 points" },
    ],
    maxTokenSeq: 2,
    ...overrides,
  };
}

describe("TokenStream", () => {
  it("renders batches inside the zero-CLS wrapper (no layout-shift regressions)", () => {
    render(<TokenStream state={streamingState()} />);
    const bubble = screen.getByTestId("token-stream");
    // CLS guards from DESIGN.md §5.2 — these classes ARE the contract.
    expect(bubble.className).toContain("max-w-[65ch]");
    expect(bubble.className).toContain("[contain:layout]");
    const body = screen.getByTestId("token-stream-body");
    expect(body.className).toContain("min-h-");
    expect(body.className).toContain("leading-[1.55]");
    expect(body).toHaveTextContent("Verstappen leads with 312 points");
  });

  it("matches the streaming structure snapshot", () => {
    const { container } = render(<TokenStream state={streamingState()} />);
    expect(container.firstChild).toMatchSnapshot();
  });

  it("announces incremental content politely and marks the busy state", () => {
    render(<TokenStream state={streamingState()} />);
    const body = screen.getByTestId("token-stream-body");
    expect(body).toHaveAttribute("aria-live", "polite");
    expect(body).toHaveAttribute("aria-atomic", "false");
    expect(body).toHaveAttribute("aria-busy", "true");
  });

  it("renders citation chips before completion when sources resolve", () => {
    render(
      <TokenStream
        state={streamingState({
          sources: [{ kind: "VECTOR", title: "2026 regulations", url: null, snippet: "snippet", score: 0.8 }],
        })}
      />,
    );
    expect(screen.getByTestId("token-stream-sources")).toBeInTheDocument();
    expect(screen.getByText("2026 regulations")).toBeInTheDocument();
  });

  it("finalizes with latency and live/cached badges and drops the caret", () => {
    const completedState: StreamState = {
      ...streamingState(),
      phase: "complete",
      completion: {
        cached: true,
        message: {
          id: "m1",
          role: "ASSISTANT",
          content: "Verstappen leads with 312 points",
          status: "COMPLETE",
          intent: null,
          cached: true,
          latencyMs: 42,
          insertedAt: "2026-06-10T00:00:00Z",
          sources: [],
        },
      },
    };
    render(<TokenStream state={completedState} />);
    const footer = screen.getByTestId("token-stream-footer");
    expect(footer).toHaveTextContent("42");
    expect(footer).toHaveTextContent("cached");
  });
});
