import { type ReactNode } from "react";

import {
  CheckIcon,
  HalfDiscIcon,
  HollowCircleIcon,
  ReplaySquareIcon,
  SignalDotIcon,
  XOctagonIcon,
} from "@/components/icons";
import { LiveTelemetry } from "@/components/telemetry/pit-wall-stats";
import { SheetContent } from "@/components/ui/sheet";
import {
  type BreakerState,
  type ServiceMode,
  type ServiceStatus,
  type SystemHealthFieldsFragment,
} from "@/graphql/generated";
import { cn } from "@/lib/utils";

function statusVisual(status: ServiceStatus): { Icon: typeof CheckIcon; className: string } {
  switch (status) {
    case "HEALTHY":
      return { Icon: SignalDotIcon, className: "text-green" };
    case "DEGRADED":
      return { Icon: HalfDiscIcon, className: "text-amber" };
    case "DOWN":
      return { Icon: XOctagonIcon, className: "text-critical" };
  }
}

function breakerVisual(state: BreakerState): { Icon: typeof CheckIcon; className: string } {
  switch (state) {
    case "CLOSED":
      return { Icon: CheckIcon, className: "text-green" };
    case "OPEN":
      return { Icon: XOctagonIcon, className: "text-amber" };
    case "HALF_OPEN":
      return { Icon: HollowCircleIcon, className: "text-amber" };
  }
}

function modeVisual(mode: ServiceMode): { Icon: typeof CheckIcon; className: string } {
  switch (mode) {
    case "LIVE":
      return { Icon: SignalDotIcon, className: "text-green" };
    case "DEGRADED":
      return { Icon: HalfDiscIcon, className: "text-amber" };
    case "SHOWCASE":
      return { Icon: ReplaySquareIcon, className: "text-amber" };
  }
}

function StatusRow({
  label,
  value,
  Icon,
  className,
}: {
  label: string;
  value: string;
  Icon: typeof CheckIcon;
  className: string;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="instrument text-meta text-text-dim">{label}</span>
      <span className={cn("instrument inline-flex items-center gap-2 text-meta", className)}>
        <Icon className="h-3.5 w-3.5" />
        {value.replace("_", " ")}
      </span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-hairline px-5 py-4">
      <h3 className="instrument mb-2 text-micro text-text-faint">{title}</h3>
      {children}
    </section>
  );
}

/**
 * PIT WALL · OPS — the public ops slide-over (DESIGN.md §3.4).
 *
 * Renders systemHealth (mode / gateway / agentService / database /
 * breakerState) plus the Phase 5 `systemStats` live telemetry, polled every
 * 30s while the panel is open only. Unmeasured values render as em-dashes —
 * telemetry-fed numbers or nothing (anti-slop rule 9).
 */
export function PitWallPanel({
  health,
  unreachable,
}: {
  health: SystemHealthFieldsFragment | null;
  unreachable: boolean;
}) {
  return (
    <SheetContent title="Pit Wall · Ops" description="Live system status for the ChatFormula1 gateway.">
      {health === null ? (
        <Section title="Mode">
          <p className="instrument flex items-center gap-2 py-2 text-meta text-text-faint">
            <XOctagonIcon className="h-3.5 w-3.5" />
            {unreachable ? "GATEWAY UNREACHABLE" : "AWAITING FIRST HEALTH SNAPSHOT"}
          </p>
          {unreachable ? (
            <p className="text-meta leading-relaxed text-text-dim">
              The gateway did not answer the health query. If this is a cold start, the wake ping
              is already in flight — try again shortly.
            </p>
          ) : null}
        </Section>
      ) : (
        <>
          <Section title="Mode">
            <StatusRow label="MODE" value={health.mode} {...modeVisual(health.mode)} />
            {health.mode === "SHOWCASE" ? (
              <p className="text-meta text-text-dim">Answers are replayed from cache — labeled, never disguised.</p>
            ) : null}
          </Section>
          <Section title="Services">
            <StatusRow label="GATEWAY" value={health.gateway} {...statusVisual(health.gateway)} />
            <StatusRow label="AGENT" value={health.agentService} {...statusVisual(health.agentService)} />
            <StatusRow label="DATABASE" value={health.database} {...statusVisual(health.database)} />
            <StatusRow label="BREAKER" value={health.breakerState} {...breakerVisual(health.breakerState)} />
          </Section>
        </>
      )}

      <Section title="Live telemetry">
        <LiveTelemetry />
      </Section>
    </SheetContent>
  );
}
