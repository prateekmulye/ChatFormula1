import { cn } from "@/lib/utils";

/**
 * Height-pre-allocating skeleton (anti-slop rule 6: no dead spinners).
 * Shimmers in azure-dim; static under reduced motion.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("skeleton-shimmer rounded-md bg-surface-2", className)}
    />
  );
}
