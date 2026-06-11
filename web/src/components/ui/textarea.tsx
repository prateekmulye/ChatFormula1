import { forwardRef, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Composer textarea: surface-3 field, azure focus ring, mono placeholder. */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "w-full resize-none rounded-md border border-hairline bg-surface-3 px-4 py-3 text-ui text-text",
        "placeholder:font-mono placeholder:text-text-faint",
        "focus-visible:outline-2 focus-visible:outline-azure focus-visible:outline-offset-0",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
