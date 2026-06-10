import { motion, useReducedMotion } from "motion/react";
import { useEffect, useMemo, useState } from "react";

import { CheckIcon, ReplaySquareIcon } from "@/components/icons";
import { type StreamState } from "@/features/chat/stream-reducer";
import { type AgentNode } from "@/graphql/generated";
import { cn } from "@/lib/utils";

/** Signal spring (DESIGN.md §2.5 --spring-signal). */
const SPRING_SIGNAL = { type: "spring", stiffness: 150, damping: 15, mass: 0.1 } as const;

const RETRIEVAL_NODES: readonly AgentNode[] = ["VECTOR_SEARCH", "WEB_SEARCH", "PARALLEL_RETRIEVAL"];

interface Slot {
  id: string;
  /** AgentNodes that map onto this slot (the retrieval slot is the fork). */
  nodes: readonly AgentNode[];
  idleLabel: string;
}

const SLOTS: readonly Slot[] = [
  { id: "analyze", nodes: ["ANALYZE_QUERY"], idleLabel: "ANALYZE" },
  { id: "route", nodes: ["ROUTE"], idleLabel: "ROUTE" },
  { id: "retrieve", nodes: RETRIEVAL_NODES, idleLabel: "RETRIEVE" },
  { id: "rank", nodes: ["RANK_CONTEXT"], idleLabel: "RANK" },
  { id: "generate", nodes: ["GENERATE"], idleLabel: "GENERATE" },
  { id: "format", nodes: ["FORMAT_RESPONSE"], idleLabel: "FORMAT" },
];

const BRANCH_LABEL: Partial<Record<AgentNode, string>> = {
  VECTOR_SEARCH: "⟨VECTOR⟩",
  WEB_SEARCH: "⟨WEB⟩",
  PARALLEL_RETRIEVAL: "⟨PARALLEL⟩",
};

const ANNOUNCEMENTS: Partial<Record<AgentNode, string>> = {
  WARMING_UP: "Warming up the inference engine.",
  ANALYZE_QUERY: "Analyzing the query.",
  ROUTE: "Routing between retrieval strategies.",
  VECTOR_SEARCH: "Vector search active.",
  WEB_SEARCH: "Web search active.",
  PARALLEL_RETRIEVAL: "Parallel retrieval active.",
  RANK_CONTEXT: "Ranking retrieved context.",
  GENERATE: "Generating response.",
  FORMAT_RESPONSE: "Formatting response.",
  REPLAYING_CACHE: "Replaying a cached answer.",
};

type SlotPhase = "idle" | "active" | "complete";

function slotLabel(slot: Slot, state: StreamState): string {
  if (slot.id !== "retrieve") return slot.idleLabel;
  const taken = state.visitedNodes.find((node) => RETRIEVAL_NODES.includes(node));
  return taken !== undefined ? (BRANCH_LABEL[taken] ?? slot.idleLabel) : slot.idleLabel;
}

function slotPhases(state: StreamState): SlotPhase[] {
  const activeIndex = SLOTS.findIndex(
    (slot) => state.currentNode !== null && slot.nodes.includes(state.currentNode),
  );
  return SLOTS.map((slot, index) => {
    if (index === activeIndex) return "active";
    const visited = slot.nodes.some((node) => state.visitedNodes.includes(node));
    if (visited || state.phase === "complete") return visited ? "complete" : "idle";
    return "idle";
  });
}

function Readout({ state }: { state: StreamState }) {
  const streamingLive = state.phase === "streaming" || state.phase === "replaying";
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!streamingLive) return;
    setElapsedSeconds(0);
    const startedAt = Date.now();
    const interval = window.setInterval(
      () => setElapsedSeconds((Date.now() - startedAt) / 1000),
      250,
    );
    return () => window.clearInterval(interval);
  }, [streamingLive]);

  const latencyMs = state.completion?.message.latencyMs ?? null;
  if (state.phase === "complete" && latencyMs !== null) {
    return <span className="tabular font-mono text-micro text-text-dim">{latencyMs}&thinsp;ms</span>;
  }
  if (streamingLive) {
    return (
      <span className="tabular font-mono text-micro text-text-dim">
        T+{elapsedSeconds.toFixed(1)}s
      </span>
    );
  }
  // No fake p95/tok-s: those numerals arrive with Phase 5 systemStats.
  return null;
}

function NodePill({
  label,
  phase,
  isGenerate,
  reducedMotion,
}: {
  label: string;
  phase: SlotPhase;
  isGenerate: boolean;
  reducedMotion: boolean;
}) {
  const breathe =
    phase === "active" && !reducedMotion
      ? {
          scale: [1, 1.03, 1],
          opacity: [0.8, 1, 0.8],
          transition: { duration: isGenerate ? 1.8 : 2.8, repeat: Infinity, ease: "easeInOut" as const },
        }
      : { scale: 1, opacity: phase === "idle" ? 0.55 : 1 };

  return (
    <motion.span
      aria-label={`${label.toLowerCase().replace(/[⟨⟩]/g, "")} — ${phase}`}
      role="img"
      initial={false}
      animate={breathe}
      className={cn(
        "instrument inline-flex shrink-0 items-center gap-1.5 rounded-sm border px-2 py-1 text-micro",
        phase === "idle" && "border-hairline text-text-faint",
        phase === "active" &&
          (isGenerate ? "glow-lime border-lime/60 text-lime" : "glow-azure border-azure/60 text-azure"),
        phase === "complete" && "border-hairline text-text-dim",
      )}
    >
      {phase === "complete" ? <CheckIcon className="h-3 w-3 text-green" /> : null}
      {label}
    </motion.span>
  );
}

function Connector({ flying, reducedMotion }: { flying: boolean; reducedMotion: boolean }) {
  return (
    <span className="relative hidden h-px min-w-3 flex-1 sm:block" aria-hidden>
      <svg className="absolute inset-0 h-full w-full overflow-visible">
        <line
          x1="0"
          y1="0.5"
          x2="100%"
          y2="0.5"
          stroke="currentColor"
          className={cn("text-azure-dim/50", flying && !reducedMotion && "marching-ants text-azure")}
        />
      </svg>
      {flying && !reducedMotion ? (
        <motion.span
          className="absolute -top-[3px] h-[7px] w-[7px] rounded-full bg-azure"
          initial={{ left: "0%", scale: 0.95, opacity: 1 }}
          animate={{ left: "92%", scale: 1.1, opacity: 0 }}
          transition={{ ...SPRING_SIGNAL, opacity: { delay: 0.35, duration: 0.2 } }}
        />
      ) : null}
    </span>
  );
}

/**
 * TelemetryStrip (DESIGN.md §4.2): the live pipeline indicator. Nodes map
 * 1:1 onto the AgentNode enum; the retrieval fork lights only the taken
 * branch; a traveling signal packet rides the connector into the active node
 * within the Doherty <400ms budget (§5.3). Reduced motion: instant labeled
 * stepper, no flight, no breathing.
 */
export function TelemetryStrip({ state }: { state: StreamState }) {
  const reducedMotion = useReducedMotion() ?? false;
  const phases = slotPhases(state);
  const activeIndex = phases.findIndex((phase) => phase === "active");

  // Transient packet flight: the connector INTO the newly-active node lights
  // for ~600ms, then the strip settles into breathing (DESIGN.md §5.3).
  const [flightIndex, setFlightIndex] = useState<number | null>(null);
  useEffect(() => {
    if (activeIndex <= 0 || reducedMotion) return;
    setFlightIndex(activeIndex - 1);
    const timeout = window.setTimeout(() => setFlightIndex(null), 600);
    return () => window.clearTimeout(timeout);
  }, [activeIndex, reducedMotion]);

  const announcement = useMemo(() => {
    if (state.phase === "complete") return "Response complete.";
    if (state.phase === "failed") return "Stream failed.";
    if (state.currentNode !== null) return ANNOUNCEMENTS[state.currentNode] ?? "";
    return "";
  }, [state.phase, state.currentNode]);

  const replaying = state.phase === "replaying";
  const warming = state.phase === "warming";

  return (
    <div
      className={cn(
        "carbon-twill border-b border-hairline bg-surface-2/80 backdrop-blur-sm",
        replaying && "border-amber/30",
      )}
    >
      <div className="mx-auto flex h-12 max-w-[1200px] items-center gap-2 overflow-x-auto px-4 sm:h-14">
        {replaying ? (
          <span className="instrument inline-flex items-center gap-2 text-meta text-amber">
            <ReplaySquareIcon className="h-3.5 w-3.5" />
            REPLAY · replayed from cache
          </span>
        ) : warming ? (
          <span className="instrument inline-flex items-center gap-2 text-meta text-amber">
            <span className="status-pulse inline-block h-2 w-2 rounded-full bg-amber" />
            WARMING UP · GRID FORMING
          </span>
        ) : (
          SLOTS.map((slot, index) => (
            <span key={slot.id} className="flex min-w-0 flex-1 items-center gap-2">
              <NodePill
                label={slotLabel(slot, state)}
                phase={phases[index] ?? "idle"}
                isGenerate={slot.id === "generate"}
                reducedMotion={reducedMotion}
              />
              {index < SLOTS.length - 1 ? (
                <Connector flying={index === flightIndex} reducedMotion={reducedMotion} />
              ) : null}
            </span>
          ))
        )}
        <span className="ml-auto shrink-0 pl-3">
          <Readout state={state} />
        </span>
      </div>
      <span aria-live="polite" className="sr-only">
        {announcement}
      </span>
    </div>
  );
}
