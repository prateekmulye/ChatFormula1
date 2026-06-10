import { useState } from "react";
import { NavLink } from "react-router-dom";

import { ApexIcon } from "@/components/icons";
import { PitWallPanel } from "@/components/telemetry/pit-wall-panel";
import { StatusBadge } from "@/components/telemetry/status-badge";
import { Sheet, SheetTrigger } from "@/components/ui/sheet";
import { useSystemHealth } from "@/features/health/use-system-health";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Chat" },
  { to: "/standings", label: "Standings" },
  { to: "/calendar", label: "Calendar" },
  { to: "/drivers", label: "Drivers" },
] as const;

/**
 * Global masthead (DESIGN.md §3.0): sticky, surface-1 + bottom hairline,
 * apex logo, 4 primary routes (Hick), StatusBadge top-right opening the
 * ops panel. Desktop nav hidden on mobile (bottom tabs take over).
 */
export function Masthead() {
  const { health, unreachable } = useSystemHealth();
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-surface-1/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-8">
          <NavLink to="/" className="flex items-center gap-2 text-text" aria-label="ChatF1 home">
            <ApexIcon className="h-5 w-5 text-azure" />
            <span className="font-display text-h3 font-semibold tracking-[-0.01em]">ChatF1</span>
          </NavLink>
          <nav aria-label="Primary" className="hidden md:block">
            <ul className="flex items-center gap-1">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      cn(
                        "rounded-sm px-3 py-2 text-ui transition-colors duration-120",
                        isActive
                          ? "text-text underline decoration-azure decoration-2 underline-offset-8"
                          : "text-text-dim hover:bg-surface-2 hover:text-text",
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <Sheet open={panelOpen} onOpenChange={setPanelOpen}>
          <SheetTrigger asChild>
            <StatusBadge mode={health?.mode ?? null} unreachable={unreachable} />
          </SheetTrigger>
          <PitWallPanel health={health} unreachable={unreachable} />
        </Sheet>
      </div>
    </header>
  );
}
