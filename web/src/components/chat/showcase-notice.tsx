import { ReplaySquareIcon } from "@/components/icons";
import { type ServiceMode } from "@/graphql/generated";

/**
 * Quiet one-line SHOWCASE notice for the chat column (anti-slop rule 9 —
 * honest states, never disguised). Renders only when the gateway reports
 * SHOWCASE mode. The composer stays enabled: SHOWCASE still answers via
 * cached replay, and replayed messages carry their own `cached` badges.
 */
export function ShowcaseNotice({ mode }: { mode: ServiceMode | null }) {
  if (mode !== "SHOWCASE") return null;
  return (
    <p
      data-testid="showcase-notice"
      role="status"
      className="mb-2 flex items-center gap-2 px-1 text-meta text-text-dim"
    >
      <ReplaySquareIcon className="h-3.5 w-3.5 shrink-0 text-amber" />
      <span>Demo mode — answers replay from cache; the live model returns at midnight UTC.</span>
    </p>
  );
}
