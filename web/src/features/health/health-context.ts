import { createContext, useContext } from "react";

import { type SystemHealthState } from "@/features/health/use-system-health";

/**
 * Shared health snapshot so the masthead StatusBadge and the chat route's
 * SHOWCASE notice read ONE query + ONE systemHealthChanged subscription
 * (mounted once in the Shell) instead of opening duplicates.
 */
export const SystemHealthContext = createContext<SystemHealthState>({
  health: null,
  unreachable: false,
});

export function useSystemHealthContext(): SystemHealthState {
  return useContext(SystemHealthContext);
}
