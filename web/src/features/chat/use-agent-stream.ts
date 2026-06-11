import { useApolloClient } from "@apollo/client";
import { useEffect, useReducer, useRef } from "react";

import {
  initialStreamState,
  reduceStreamEvent,
  type StreamState,
} from "@/features/chat/stream-reducer";
import { AgentStreamDocument, type AgentStreamSubscription } from "@/graphql/generated";

type StreamAction =
  | { kind: "event"; event: NonNullable<AgentStreamSubscription["agentStream"]> }
  | { kind: "reset" }
  | { kind: "transport-error" };

function reducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.kind) {
    case "event":
      return reduceStreamEvent(state, action.event);
    case "reset":
      return initialStreamState;
    case "transport-error":
      // The socket retries automatically and the gateway replays the buffer;
      // only surface an error if the stream never terminated by itself.
      if (state.phase === "complete" || state.phase === "failed") return state;
      return {
        ...state,
        phase: "failed",
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: "Stream connection lost — the gateway may be restarting.",
          retryable: true,
        },
      };
  }
}

/**
 * Subscribes to agentStream(messageId) and reduces the AgentEvent union into
 * StreamState. Idempotent by seq; a detected gap fires `onGap` exactly once
 * (the caller refetches the message from Postgres — ARCHITECTURE §4.5).
 */
export function useAgentStream(messageId: string | null, onGap: () => void): StreamState {
  const client = useApolloClient();
  const [state, dispatch] = useReducer(reducer, initialStreamState);
  const gapHandledRef = useRef(false);
  const onGapRef = useRef(onGap);
  onGapRef.current = onGap;

  useEffect(() => {
    dispatch({ kind: "reset" });
    gapHandledRef.current = false;
    if (messageId === null) return;

    const subscription = client
      .subscribe<AgentStreamSubscription>({
        query: AgentStreamDocument,
        variables: { messageId },
        fetchPolicy: "no-cache",
      })
      .subscribe({
        next: (result) => {
          const event = result.data?.agentStream;
          if (event != null) dispatch({ kind: "event", event });
        },
        error: () => dispatch({ kind: "transport-error" }),
      });

    return () => subscription.unsubscribe();
  }, [client, messageId]);

  useEffect(() => {
    if (state.gapDetected && !gapHandledRef.current) {
      gapHandledRef.current = true;
      onGapRef.current();
    }
  }, [state.gapDetected]);

  return state;
}
