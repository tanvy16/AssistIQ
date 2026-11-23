import { fetchDashboardSummary } from "./dashboard";
import { usePolledQuery } from "./usePolledQuery";
import type { DashboardSummary } from "./dashboard.types";

const POLL_MS = 20_000;
const TTL_MS = 15_000;

export function useDashboard(accessToken: string | null) {
  const { data, error, isLoading, updatedAt, live, refresh } = usePolledQuery<DashboardSummary>({
    enabled: Boolean(accessToken),
    cacheKey: `dashboard:${accessToken ?? "anon"}`,
    intervalMs: POLL_MS,
    ttlMs: TTL_MS,
    fetcher: (signal) => fetchDashboardSummary(accessToken as string, signal),
  });

  return { data, error, isLoading, updatedAt, live, refresh };
}
