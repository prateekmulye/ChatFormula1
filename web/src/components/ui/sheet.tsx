import * as DialogPrimitive from "@radix-ui/react-dialog";
import { type ComponentPropsWithoutRef, type ReactNode } from "react";

import { CloseIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/**
 * Right-side slide-over (shadcn Sheet on Radix Dialog): focus-trapped dialog,
 * Esc closes, focus returns to the trigger. Grace transition 560ms ease-reveal
 * (DESIGN.md §4.1); instant under reduced motion.
 */
export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;

interface SheetContentProps extends ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  title: string;
  description?: string;
  children: ReactNode;
}

export function SheetContent({ title, description, children, className, ...props }: SheetContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="sheet-overlay fixed inset-0 z-40 bg-bg/70 backdrop-blur-sm" />
      <DialogPrimitive.Content
        className={cn(
          "sheet-panel fixed inset-y-0 right-0 z-50 flex w-full flex-col gap-0 overflow-y-auto",
          "border-l border-hairline-2 bg-surface-1 sm:max-w-md",
          className,
        )}
        {...props}
      >
        <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
          <DialogPrimitive.Title className="instrument text-meta text-text">
            {title}
          </DialogPrimitive.Title>
          <DialogPrimitive.Close
            className="rounded-sm p-2 text-text-dim hover:bg-surface-2 hover:text-text"
            aria-label="Close panel"
          >
            <CloseIcon className="h-4 w-4" />
          </DialogPrimitive.Close>
        </div>
        {description !== undefined ? (
          <DialogPrimitive.Description className="sr-only">{description}</DialogPrimitive.Description>
        ) : null}
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
