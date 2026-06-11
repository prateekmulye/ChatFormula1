import { useState } from "react";
import { toast } from "sonner";

import { ThumbDownIcon, ThumbUpIcon } from "@/components/icons";
import { useSubmitFeedbackMutation } from "@/graphql/generated";
import { cn } from "@/lib/utils";

type Verdict = "up" | "down";

/**
 * Thumbs up/down for a completed assistant message (DESIGN.md §4.2
 * TokenStream footer row). Optimistic: the glyph lights immediately and
 * reverts only if the mutation fails. Switching verdicts re-submits — the
 * gateway upserts per viewer+message, so updates are idempotent. Re-clicking
 * the active verdict is a no-op (nothing to change).
 *
 * Glyphs are drawn SVGs from the original icon set (anti-slop rule 3).
 * 44px hit targets (Fitts) with negative margin so the footer row stays slim.
 */
export function FeedbackControls({ messageId }: { messageId: string }) {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [submitFeedback] = useSubmitFeedbackMutation();

  const submit = (next: Verdict) => {
    const previous = verdict;
    if (previous === next) return;
    setVerdict(next);
    void submitFeedback({ variables: { messageId, helpful: next === "up" } }).catch(() => {
      setVerdict(previous);
      toast.warning("Feedback did not reach the gateway", {
        description: "The verdict was not recorded — try again in a moment.",
      });
    });
  };

  const buttonClass = (active: boolean, activeColor: string) =>
    cn(
      "-my-3 flex h-11 w-11 items-center justify-center rounded-sm transition-colors duration-120",
      "hover:bg-surface-2",
      active ? activeColor : "text-text-faint hover:text-text-dim",
    );

  return (
    <div role="group" aria-label="Was this answer helpful?" className="ml-auto flex items-center">
      <button
        type="button"
        aria-pressed={verdict === "up"}
        aria-label="Helpful"
        onClick={() => submit("up")}
        className={buttonClass(verdict === "up", "text-green")}
      >
        <ThumbUpIcon className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        aria-pressed={verdict === "down"}
        aria-label="Not helpful"
        onClick={() => submit("down")}
        className={buttonClass(verdict === "down", "text-amber")}
      >
        <ThumbDownIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
