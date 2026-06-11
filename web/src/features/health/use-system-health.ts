import { useMemo } from "react";

import {
  type SystemHealthFieldsFragment,
  useSystemHealthChangedSubscription,
  useSystemHealthQuery,
} from "@/graphql/generated";

export interface SystemHealthState {
  /** Latest known health snapshot, or null before the first response. */
  readonly health: SystemHealthFieldsFragment | null;
  /** True when the gateway itself cannot be reached (no snapshot is trustworthy). */
  readonly unreachable: boolean;
}

/**
 * systemHealth query (with a slow recovery poll) merged with the
 * systemHealthChanged subscription so badges flip in real time.
 */
export function useSystemHealth(): SystemHealthState {
  const { data, error } = useSystemHealthQuery({
    pollInterval: 30_000,
    notifyOnNetworkStatusChange: true,
  });
  const { data: changed } = useSystemHealthChangedSubscription();

  return useMemo(() => {
    const health = changed?.systemHealthChanged ?? data?.systemHealth ?? null;
    return { health, unreachable: error !== undefined && data === undefined };
  }, [changed, data, error]);
}
