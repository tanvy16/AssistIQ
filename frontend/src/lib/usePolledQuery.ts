import { useCallback, useEffect, useRef, useState } from "react";

import { memoryGet, memoryGetAt, memoryLoad } from "./queryMemory";

type UsePolledQueryOptions<T> = {
  enabled: boolean;
  cacheKey: string;
  intervalMs: number;
  ttlMs?: number;
  fetcher: (signal: AbortSignal) => Promise<T>;
};

function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

export function usePolledQuery<T>({
  enabled,
  cacheKey,
  intervalMs,
  ttlMs = 15_000,
  fetcher,
}: UsePolledQueryOptions<T>) {
  const cached = enabled ? memoryGet<T>(cacheKey, ttlMs) : undefined;
  const [data, setData] = useState<T | null>(cached ?? null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(enabled && cached === undefined));
  const [updatedAt, setUpdatedAt] = useState<Date | null>(() => {
    const at = cached !== undefined ? memoryGetAt(cacheKey) : undefined;
    return at ? new Date(at) : null;
  });
  const [live, setLive] = useState(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  // The controller of the request currently in flight for THIS mounted effect.
  // A per-controller handle (instead of a boolean) means StrictMode's
  // mount -> cleanup -> mount cycle, or a cacheKey change, never leaves a stale
  // "busy" flag that would silently skip the next initial load.
  const inflight = useRef<AbortController | null>(null);
  const cacheKeyRef = useRef(cacheKey);

  useEffect(() => {
    if (cacheKeyRef.current === cacheKey) return;
    cacheKeyRef.current = cacheKey;
    const nextCached = memoryGet<T>(cacheKey, ttlMs);
    setData(nextCached ?? null);
    setIsLoading(Boolean(enabled && nextCached === undefined));
    setError(null);
    setLive(false);
  }, [cacheKey, enabled, ttlMs]);

  const load = useCallback(
    async (mode: "initial" | "refresh", controller: AbortController) => {
      const signal = controller.signal;
      if (!enabled) return;
      // Prevent overlapping polls: a refresh never stacks on a live request.
      if (mode === "refresh" && inflight.current && !inflight.current.signal.aborted) return;
      inflight.current = controller;
      if (mode === "initial" && memoryGet<T>(cacheKey, ttlMs) === undefined) {
        setIsLoading(true);
      }
      try {
        const next = await memoryLoad(cacheKey, () => fetcherRef.current(signal), {
          force: mode === "refresh",
          ttlMs,
        });
        if (signal.aborted) return;
        setData(next);
        setError(null);
        // memoryLoad stores fetch time; a cache hit keeps its original time so
        // "Updated" never claims a fresher snapshot than we actually have.
        setUpdatedAt(new Date(memoryGetAt(cacheKey) ?? Date.now()));
        setLive(document.visibilityState !== "hidden");
      } catch (err) {
        if (signal.aborted || isAbortError(err)) return;
        setError(err instanceof Error ? err.message : "Request failed");
        setLive(false);
      } finally {
        if (inflight.current === controller) inflight.current = null;
        if (!signal.aborted) setIsLoading(false);
      }
    },
    [cacheKey, enabled, ttlMs],
  );

  useEffect(() => {
    if (!enabled) return;
    const pending = new Set<AbortController>();
    const run = (mode: "initial" | "refresh") => {
      const controller = new AbortController();
      pending.add(controller);
      void load(mode, controller).finally(() => pending.delete(controller));
    };
    run("initial");
    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden") {
        setLive(false);
        return;
      }
      run("refresh");
    }, intervalMs);
    const onVisibility = () => {
      if (document.visibilityState === "visible") run("refresh");
      else setLive(false);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
      pending.forEach((controller) => controller.abort());
      inflight.current = null;
    };
  }, [enabled, intervalMs, load]);

  return {
    data,
    error,
    isLoading,
    updatedAt,
    live,
    refresh: () => {
      void load("refresh", new AbortController());
    },
  };
}
