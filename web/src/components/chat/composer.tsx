import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";

import { BoltIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useRateLimitStatusQuery } from "@/graphql/generated";

const MAX_LENGTH = 2000;

/**
 * Sticky composer (DESIGN.md §3.1): mono placeholder, azure send, Enter
 * sends / Shift+Enter breaks (documented for AT via aria-describedby).
 * Focus stays here after send — the console rapid-fire pattern. The
 * rateLimitStatus hint is deliberately subtle mono metadata.
 */
export function Composer({
  onSend,
  busy,
}: {
  onSend: (content: string) => void;
  /** True while a stream is active — sending is held, focus is not. */
  busy: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { data: rateLimit } = useRateLimitStatusQuery({ fetchPolicy: "cache-first" });

  const trimmed = value.trim();
  const canSend = !busy && trimmed.length > 0 && trimmed.length <= MAX_LENGTH;

  const submit = () => {
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
    textareaRef.current?.focus();
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-1.5">
      <div className="flex items-end gap-2">
        <label htmlFor="composer" className="sr-only">
          Ask the pit wall
        </label>
        <Textarea
          id="composer"
          ref={textareaRef}
          rows={1}
          maxLength={MAX_LENGTH}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="▸ Ask the pit wall…"
          aria-describedby="composer-help"
          className="max-h-40 field-sizing-content"
        />
        <Button type="submit" size="icon" disabled={!canSend} aria-label="Send message">
          <BoltIcon className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex items-center justify-between gap-2 px-1">
        <span id="composer-help" className="text-micro text-text-faint">
          Enter to send · Shift+Enter for a new line
        </span>
        {rateLimit !== undefined ? (
          <span className="tabular font-mono text-micro text-text-faint">
            {rateLimit.rateLimitStatus.remainingMinute}/{rateLimit.rateLimitStatus.limitPerMinute}{" "}
            req·min
          </span>
        ) : null}
      </div>
    </form>
  );
}
