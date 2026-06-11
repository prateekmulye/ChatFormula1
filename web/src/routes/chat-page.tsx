import { useEffect, useRef, useState } from "react";

import { Composer } from "@/components/chat/composer";
import { LightsOutLoader } from "@/components/chat/lights-out-loader";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { AssistantMessage, TokenStream } from "@/components/chat/token-stream";
import { CountdownHero } from "@/components/standings/countdown-hero";
import { TelemetryStrip } from "@/components/telemetry/telemetry-strip";
import { Button } from "@/components/ui/button";
import { type StreamPhase } from "@/features/chat/stream-reducer";
import { useChat } from "@/features/chat/use-chat";
import { useNextRaceQuery } from "@/graphql/generated";

/**
 * Warming → streaming handoff: keep the LightsOutLoader mounted through its
 * 400ms green resolution flash before swapping in the TokenStream (§5.1).
 */
function useWarmingHandoff(phase: StreamPhase): "none" | "loader" | "resolving" {
  const [handoff, setHandoff] = useState<"none" | "loader" | "resolving">("none");

  useEffect(() => {
    if (phase === "warming") {
      setHandoff("loader");
      return;
    }
    if (phase === "idle" || phase === "failed") {
      setHandoff("none");
      return;
    }
    setHandoff((current) => (current === "loader" ? "resolving" : current));
  }, [phase]);

  useEffect(() => {
    if (handoff !== "resolving") return;
    const timeout = window.setTimeout(() => setHandoff("none"), 700);
    return () => window.clearTimeout(timeout);
  }, [handoff]);

  return handoff;
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[65ch] rounded-[14px] rounded-br-[4px] border border-hairline bg-surface-2 px-4 py-3 font-mono text-ui text-text">
        {content}
      </p>
    </div>
  );
}

function daypart(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Late night";
  if (hour < 12) return "Morning";
  if (hour < 18) return "Afternoon";
  return "Evening";
}

function EmptyState({ onPick, disabled }: { onPick: (q: string) => void; disabled: boolean }) {
  const { data } = useNextRaceQuery();
  const nextRace = data?.nextRace ?? null;

  return (
    <div className="flex flex-col items-start gap-6 py-12">
      <div>
        <h1 className="font-display text-h1 font-medium tracking-[-0.01em] text-text">
          {daypart()}. The pit wall is listening.
        </h1>
        <p className="mt-2 max-w-[55ch] text-body text-text-dim">
          Ask anything Formula 1 — standings, strategy, regulations. Watch the pipeline strip
          above: every answer shows you which node is working while it streams.
        </p>
      </div>
      <SuggestionChips onPick={onPick} disabled={disabled} />
      {nextRace !== null ? (
        <div className="w-full max-w-md">
          <CountdownHero race={nextRace} compact />
        </div>
      ) : null}
    </div>
  );
}

export function ChatPage() {
  const chat = useChat();
  const handoff = useWarmingHandoff(chat.stream.phase);
  const endRef = useRef<HTMLDivElement>(null);
  const activeBubbleRef = useRef<HTMLDivElement>(null);

  const busy =
    chat.activeMessageId !== null &&
    chat.stream.phase !== "failed" &&
    chat.stream.phase !== "complete";

  // Keep the latest exchange in view as content arrives.
  const segmentCount = chat.stream.segments.length;
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [chat.items.length, segmentCount, handoff]);

  // Focus moves to the assistant message once it begins streaming (§6 Composer).
  const streamingStarted = chat.stream.phase === "streaming" || chat.stream.phase === "replaying";
  useEffect(() => {
    if (streamingStarted) activeBubbleRef.current?.focus({ preventScroll: true });
  }, [streamingStarted]);

  const showLoader = handoff !== "none";
  const showActiveBubble =
    chat.activeMessageId !== null && !showLoader && chat.stream.phase !== "idle";

  return (
    <div className="flex min-h-full flex-col">
      <div className="sticky top-14 z-20">
        <TelemetryStrip state={chat.stream} />
      </div>

      <div className="mx-auto flex w-[min(760px,92vw)] flex-1 flex-col gap-4 py-6">
        {chat.items.length === 0 && chat.activeMessageId === null ? (
          <EmptyState onPick={chat.send} disabled={busy} />
        ) : (
          <ol className="flex flex-col gap-4" aria-label="Conversation">
            {chat.items.map((item) => (
              <li key={item.id}>
                {item.kind === "user" ? (
                  <UserBubble content={item.content} />
                ) : (
                  <AssistantMessage
                    content={item.message.content}
                    sources={item.message.sources}
                    latencyMs={item.message.latencyMs ?? null}
                    cached={item.message.cached}
                  />
                )}
              </li>
            ))}

            {showLoader ? (
              <li>
                <LightsOutLoader resolved={handoff === "resolving"} onRetry={chat.retry} />
              </li>
            ) : null}

            {showActiveBubble ? (
              <li>
                <div ref={activeBubbleRef} tabIndex={-1} className="outline-none">
                  <TokenStream state={chat.stream} />
                  {chat.stream.phase === "failed" && chat.canRetry ? (
                    <Button variant="secondary" size="sm" className="mt-2" onClick={chat.retry}>
                      Re-send
                    </Button>
                  ) : null}
                  {chat.reconciling ? (
                    <p className="instrument mt-2 text-micro text-text-faint">
                      seq gap detected · re-syncing from the gateway record
                    </p>
                  ) : null}
                </div>
              </li>
            ) : null}
          </ol>
        )}

        <div ref={endRef} />

        {chat.items.length > 0 && !busy ? (
          <div className="mt-auto pt-2">
            <SuggestionChips onPick={chat.send} disabled={busy} />
          </div>
        ) : null}
      </div>

      <div className="sticky bottom-14 z-20 border-t border-hairline bg-bg/95 py-3 backdrop-blur-sm md:bottom-0">
        <div className="mx-auto w-[min(760px,92vw)]">
          <Composer onSend={chat.send} busy={busy} />
        </div>
      </div>
    </div>
  );
}
