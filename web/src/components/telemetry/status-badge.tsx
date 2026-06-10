import { forwardRef } from "react";

import { HalfDiscIcon, ReplaySquareIcon, SignalDotIcon, XOctagonIcon } from "@/components/icons";
import { type ServiceMode } from "@/graphql/generated";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  /** Current service mode, or null while unknown. */
  mode: ServiceMode | null;
  /** Gateway unreachable — overrides mode with an honest OFFLINE state. */
  unreachable?: boolean;
  onClick?: () => void;
}

interface BadgeVisual {
  label: string;
  srHint: string;
  Icon: typeof SignalDotIcon;
  className: string;
  pulse: boolean;
}

function visualFor(mode: ServiceMode | null, unreachable: boolean): BadgeVisual {
  if (unreachable) {
    return {
      label: "OFFLINE",
      srHint: "Gateway unreachable.",
      Icon: XOctagonIcon,
      className: "text-text-faint border-hairline",
      pulse: false,
    };
  }
  switch (mode) {
    case "LIVE":
      return {
        label: "LIVE",
        srHint: "Live inference.",
        Icon: SignalDotIcon,
        className: "text-green border-hairline",
        pulse: true,
      };
    case "DEGRADED":
      return {
        label: "DEGRADED",
        srHint: "Degraded — circuit breaker open or upstream trouble.",
        Icon: HalfDiscIcon,
        className: "text-amber border-hairline",
        pulse: true,
      };
    case "SHOWCASE":
      return {
        label: "SHOWCASE",
        srHint: "Showcase — answers replayed from cache.",
        Icon: ReplaySquareIcon,
        className: "text-amber border-hairline",
        pulse: true,
      };
    case null:
      return {
        label: "······",
        srHint: "Checking system status.",
        Icon: HollowDot,
        className: "text-text-faint border-hairline",
        pulse: false,
      };
  }
}

function HollowDot(props: Parameters<typeof SignalDotIcon>[0]) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden {...props}>
      <circle cx="12" cy="12" r="5" />
    </svg>
  );
}

/**
 * The LIVE / DEGRADED / SHOWCASE pill (DESIGN.md §4.2): glyph + color + mono
 * label, never color alone. Click opens the PitWallPanel; lives in the
 * masthead AND at the top of the panel (shared component).
 */
export const StatusBadge = forwardRef<HTMLButtonElement, StatusBadgeProps>(
  ({ mode, unreachable = false, onClick }, ref) => {
    const visual = visualFor(mode, unreachable);
    const { Icon } = visual;
    return (
      <button
        ref={ref}
        type="button"
        onClick={onClick}
        aria-haspopup="dialog"
        aria-label={`System status: ${visual.label.toLowerCase()}. ${visual.srHint} Open ops panel.`}
        className={cn(
          "instrument inline-flex min-h-11 items-center gap-2 rounded-sm border bg-surface-2 px-3 py-1.5 text-meta",
          "transition-colors duration-120 hover:border-hairline-2",
          visual.className,
        )}
      >
        <Icon className={cn("h-3 w-3", visual.pulse && "status-pulse")} />
        <span>{visual.label}</span>
      </button>
    );
  },
);
StatusBadge.displayName = "StatusBadge";
