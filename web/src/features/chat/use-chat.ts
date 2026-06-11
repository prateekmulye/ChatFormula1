import { useApolloClient } from "@apollo/client";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { humanizeStreamError } from "@/features/chat/error-copy";
import { type StreamState } from "@/features/chat/stream-reducer";
import { useAgentStream } from "@/features/chat/use-agent-stream";
import {
  ConversationMessagesDocument,
  type ConversationMessagesQuery,
  type ConversationMessagesQueryVariables,
  type MessageFieldsFragment,
  useSendMessageMutation,
  useStartConversationMutation,
} from "@/graphql/generated";

export type ChatItem =
  | { kind: "user"; id: string; content: string }
  | { kind: "assistant"; id: string; message: MessageFieldsFragment };

export interface ChatSession {
  readonly items: readonly ChatItem[];
  /** Stream state for the in-flight assistant message (idle when none). */
  readonly stream: StreamState;
  readonly activeMessageId: string | null;
  /** True while a gap refetch is reconciling against Postgres. */
  readonly reconciling: boolean;
  readonly send: (content: string) => void;
  readonly retry: () => void;
  readonly canRetry: boolean;
}

const GAP_REFETCH_ATTEMPTS = 6;
const GAP_REFETCH_DELAY_MS = 1500;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Conversation state machine for the chat route: lazily starts a
 * conversation, sends messages, drives the per-message agentStream, and
 * reconciles seq gaps by refetching the message from Postgres
 * (ARCHITECTURE §4.5 — the completed message is always authoritative there).
 */
export function useChat(): ChatSession {
  const client = useApolloClient();
  const [startConversation] = useStartConversationMutation();
  const [sendMessage] = useSendMessageMutation();

  const conversationIdRef = useRef<string | null>(null);
  const [items, setItems] = useState<readonly ChatItem[]>([]);
  const [active, setActive] = useState<{ id: string; question: string } | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const finalizedRef = useRef<Set<string>>(new Set());

  const finalize = useCallback((message: MessageFieldsFragment) => {
    if (finalizedRef.current.has(message.id)) return;
    finalizedRef.current.add(message.id);
    setItems((current) => [...current, { kind: "assistant", id: message.id, message }]);
    setActive(null);
    setReconciling(false);
  }, []);

  /** Gap recovery: poll the conversation until the message lands as COMPLETE/FAILED. */
  const reconcileFromPostgres = useCallback(
    async (messageId: string) => {
      const conversationId = conversationIdRef.current;
      if (conversationId === null) return;
      setReconciling(true);
      for (let attempt = 0; attempt < GAP_REFETCH_ATTEMPTS; attempt += 1) {
        if (finalizedRef.current.has(messageId)) return;
        const { data } = await client.query<
          ConversationMessagesQuery,
          ConversationMessagesQueryVariables
        >({
          query: ConversationMessagesDocument,
          variables: { id: conversationId },
          fetchPolicy: "network-only",
        });
        const message = data.conversation?.messages.find((m) => m.id === messageId);
        if (message !== undefined && (message.status === "COMPLETE" || message.status === "FAILED")) {
          finalize(message);
          return;
        }
        await sleep(GAP_REFETCH_DELAY_MS);
      }
      setReconciling(false);
    },
    [client, finalize],
  );

  const onGap = useCallback(() => {
    const messageId = active?.id;
    if (messageId !== undefined) void reconcileFromPostgres(messageId);
  }, [active, reconcileFromPostgres]);

  const stream = useAgentStream(active?.id ?? null, onGap);

  // Live completion path (the gap refetch races this; finalize is idempotent).
  // The gateway does not yet persist SourcesResolved onto the message row
  // (Phase 5 work), so the live-stream sources are merged in — they came off
  // the same authorized subscription, not invented client-side.
  useEffect(() => {
    if (stream.phase === "complete" && stream.completion !== null) {
      const message = stream.completion.message;
      const sources = stream.sources !== null ? [...stream.sources] : message.sources;
      finalize({ ...message, sources });
    }
  }, [stream.phase, stream.completion, stream.sources, finalize]);

  // Error surfacing: amber retryable toast / critical non-retryable (§4.2).
  useEffect(() => {
    if (stream.error === null) return;
    if (stream.error.retryable) {
      toast.warning("Pit wall reports a hiccup", {
        description: humanizeStreamError(stream.error),
      });
    } else {
      toast.error("Stream failed", { description: humanizeStreamError(stream.error) });
    }
  }, [stream.error]);

  const send = useCallback(
    (content: string) => {
      void (async () => {
        try {
          let conversationId = conversationIdRef.current;
          if (conversationId === null) {
            const started = await startConversation();
            conversationId = started.data?.startConversation.id ?? null;
            if (conversationId === null) throw new Error("startConversation returned no id");
            conversationIdRef.current = conversationId;
          }
          const result = await sendMessage({ variables: { conversationId, content } });
          const payload = result.data?.sendMessage;
          if (payload === undefined) throw new Error("sendMessage returned no payload");
          setItems((current) => [
            ...current,
            { kind: "user", id: payload.userMessage.id, content: payload.userMessage.content },
          ]);
          setActive({ id: payload.assistantMessageId, question: content });
        } catch (error) {
          toast.error("Could not reach the gateway", {
            description: error instanceof Error ? error.message : "Unknown transport error.",
          });
        }
      })();
    },
    [sendMessage, startConversation],
  );

  const retry = useCallback(() => {
    const question = active?.question;
    setActive(null);
    if (question !== undefined) send(question);
  }, [active, send]);

  return {
    items,
    stream,
    activeMessageId: active?.id ?? null,
    reconciling,
    send,
    retry,
    canRetry: stream.error?.retryable === true,
  };
}
