import { fetchObservabilityDashboard } from "./observability";
import { usePolledQuery } from "./usePolledQuery";
import type { ObservabilityDashboard, TimeRangeKey } from "./observability.types";

const POLL_MS = 45_000;
const TTL_MS = 20_000;

export function useObservability(
  accessToken: string | null,
  range: TimeRangeKey,
  customStart: string,
  customEnd: string,
) {
  const customIncomplete = range === "custom" && (!customStart || !customEnd);
  const cacheKey = `observability:${accessToken ?? "anon"}:${range}:${customStart}:${customEnd}`;

  const { data, error, isLoading, updatedAt, live } = usePolledQuery<ObservabilityDashboard>({
    enabled: Boolean(accessToken) && !customIncomplete,
    cacheKey,
    intervalMs: POLL_MS,
    ttlMs: TTL_MS,
    fetcher: (signal) =>
      fetchObservabilityDashboard(
        accessToken as string,
        range,
        customStart || undefined,
        customEnd || undefined,
        signal,
      ),
  });

  return { data, error, isLoading, updatedAt, live };
}
