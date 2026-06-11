import { type ReactNode } from "react";

import { SystemHealthContext } from "@/features/health/health-context";
import { useSystemHealth } from "@/features/health/use-system-health";

/** Mounts the single health query + subscription; consumers use the context. */
export function SystemHealthProvider({ children }: { children: ReactNode }) {
  const state = useSystemHealth();
  return <SystemHealthContext.Provider value={state}>{children}</SystemHealthContext.Provider>;
}
