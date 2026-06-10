import { type ReactNode } from "react";

import { Footer } from "@/components/layout/footer";
import { Masthead } from "@/components/layout/masthead";
import { MobileTabs } from "@/components/layout/mobile-tabs";

/**
 * Global shell (DESIGN.md §3.0): skip link, semantic landmarks, masthead,
 * route content, persistent disclaimer footer, mobile bottom tabs, and the
 * single fixed carbon-grain layer.
 */
export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-azure px-4 py-2 text-bg focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <div className="carbon-grain" aria-hidden />
      <Masthead />
      <main id="main" className="relative z-10 flex-1">
        {children}
      </main>
      <Footer />
      <MobileTabs />
    </div>
  );
}
