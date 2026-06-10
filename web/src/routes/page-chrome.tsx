import { CautionTriangleIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";

/** One visible h1 per route, Spectral display voice. */
export function PageHeading({ title, kicker }: { title: string; kicker: string }) {
  return (
    <header>
      <p className="instrument text-meta text-azure">{kicker}</p>
      <h1 className="mt-1 font-display text-h1 font-medium tracking-[-0.01em] text-text">{title}</h1>
    </header>
  );
}

/** Honest data-fetch failure block — amber, retryable, never a dead spinner. */
export function DataError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mt-6 flex flex-col items-start gap-3 rounded-lg border border-amber/40 bg-surface-1 px-5 py-4">
      <p className="flex items-start gap-2 text-ui text-text-dim">
        <CautionTriangleIcon className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
        {message}
      </p>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
