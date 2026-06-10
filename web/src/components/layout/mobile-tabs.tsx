import { NavLink } from "react-router-dom";

import { CalendarIcon, PodiumIcon, RadioIcon, WheelIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "/", label: "Chat", Icon: RadioIcon },
  { to: "/standings", label: "Standings", Icon: PodiumIcon },
  { to: "/calendar", label: "Calendar", Icon: CalendarIcon },
  { to: "/drivers", label: "Drivers", Icon: WheelIcon },
] as const;

/** Mobile bottom tab bar (DESIGN.md §3.0): icons + labels, ≥44px targets. */
export function MobileTabs() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-hairline bg-surface-1/95 backdrop-blur-sm md:hidden"
    >
      <ul className="flex h-14">
        {TABS.map(({ to, label, Icon }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex h-full min-h-11 flex-col items-center justify-center gap-0.5",
                  isActive ? "text-azure" : "text-text-dim",
                )
              }
            >
              <Icon className="h-5 w-5" />
              <span className="instrument text-micro">{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
