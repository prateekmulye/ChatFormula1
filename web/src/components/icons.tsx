import { type SVGProps } from "react";

/**
 * Original inline-SVG icon set (DESIGN.md §4.3): currentColor, 1.5px stroke,
 * geometric/instrument style. No emoji, no F1 marks. Status glyphs differ in
 * SHAPE so they read without color.
 *
 * All icons are decorative by default (`aria-hidden`) — pair them with a
 * visible or SR-only text label at the call site.
 */
type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps): IconProps {
  return {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    ...props,
  };
}

/** The logo — a stylized racing apex / cornering line. */
export function ApexIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 19 L11 5 L13 5 L20 19" />
      <path d="M8.5 13.5 Q12 10.5 15.5 13.5" strokeWidth={1.2} />
    </svg>
  );
}

/** Filled signal dot — LIVE / healthy / active node. */
export function SignalDotIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Filled diamond — VECTOR source. */
export function VectorDiamondIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 4 L20 12 L12 20 L4 12 Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Hollow diamond — WEB source. */
export function WebDiamondIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 4.5 L19.5 12 L12 19.5 L4.5 12 Z" />
    </svg>
  );
}

/** Check — complete / healthy. */
export function CheckIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 12.5 L10 17.5 L19 7" />
    </svg>
  );
}

/** Caution triangle — degraded / warning (the drawn ⚠, never an emoji). */
export function CautionTriangleIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 4 L21 19 L3 19 Z" />
      <path d="M12 10 L12 14.5" />
      <circle cx="12" cy="16.8" r="0.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** X-octagon — down / critical. */
export function XOctagonIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M8.5 3.5 L15.5 3.5 L20.5 8.5 L20.5 15.5 L15.5 20.5 L8.5 20.5 L3.5 15.5 L3.5 8.5 Z" />
      <path d="M9.5 9.5 L14.5 14.5 M14.5 9.5 L9.5 14.5" />
    </svg>
  );
}

/** Half disc ◐ — degraded mode. */
export function HalfDiscIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="7" />
      <path d="M12 5 A7 7 0 0 1 12 19 Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Square-in-square ▣ — showcase / replayed from cache. */
export function ReplaySquareIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4.5" y="4.5" width="15" height="15" rx="1.5" />
      <rect x="9" y="9" width="6" height="6" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Hollow circle ◯ — half-open breaker / probing. */
export function HollowCircleIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="6" />
    </svg>
  );
}

/** Clean lightning glyph ⌁ — energy / send. */
export function BoltIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M13 3 L6 13.5 L11 13.5 L9.5 21 L18 9.5 L12.5 9.5 Z" />
    </svg>
  );
}

/** Clock — latency / uptime. */
export function ClockIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7.5 L12 12 L15.5 14" />
    </svg>
  );
}

/** Shield — guardrail. */
export function ShieldIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3.5 L19 6.5 L19 12 C19 16.5 16 19.5 12 21 C8 19.5 5 16.5 5 12 L5 6.5 Z" />
    </svg>
  );
}

/** Loop — idempotent / retry. */
export function LoopIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 12 A7 7 0 1 1 7.5 17.5" />
      <path d="M5 17.5 L7.5 17.5 L7.5 15" />
    </svg>
  );
}

/** Arrow — transit. */
export function ArrowRightIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 12 L19 12 M13.5 6.5 L19 12 L13.5 17.5" />
    </svg>
  );
}

/** Close ✕ — sheet / dismiss. */
export function CloseIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 6 L18 18 M18 6 L6 18" />
    </svg>
  );
}

/* ── Navigation glyphs ──────────────────────────────────────────────────────── */

/** Chat — pit-radio headset. */
export function RadioIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 13 A7 7 0 0 1 19 13" />
      <rect x="3.5" y="13" width="3.5" height="6" rx="1.5" />
      <rect x="17" y="13" width="3.5" height="6" rx="1.5" />
      <path d="M19 19 Q19 21 16 21 L14 21" />
    </svg>
  );
}

/** Standings — podium bars. */
export function PodiumIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="9" y="6" width="6" height="14" />
      <rect x="3" y="11" width="6" height="9" />
      <rect x="15" y="14" width="6" height="6" />
    </svg>
  );
}

/** Calendar — month grid with a marked slot. */
export function CalendarIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="5.5" width="16" height="14.5" rx="1.5" />
      <path d="M4 9.5 L20 9.5 M8.5 3.5 L8.5 7 M15.5 3.5 L15.5 7" />
      <circle cx="12" cy="14.5" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Drivers — steering wheel. */
export function WheelIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="2" />
      <path d="M4.2 11 L10 11 M14 11 L19.8 11 M12 14 L12 19.8" />
    </svg>
  );
}
