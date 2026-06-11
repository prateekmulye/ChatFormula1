import { cva, type VariantProps } from "class-variance-authority";
import { type ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

/** shadcn-style Button themed onto the Telemetry Noir tokens (DESIGN.md §4.1). */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-ui font-medium transition-colors duration-120 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-azure text-bg hover:bg-azure/85",
        secondary: "bg-surface-2 text-text border border-hairline hover:border-hairline-2",
        ghost: "text-text-dim hover:bg-surface-2 hover:text-text",
      },
      size: {
        default: "h-11 px-4",
        sm: "h-9 px-3 text-meta",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type, ...props }, ref) => (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
