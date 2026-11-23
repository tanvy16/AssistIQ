type MemoryEntry<T> = {
  value?: T;
  at: number;
  inflight?: Promise<T>;
};

const store = new Map<string, MemoryEntry<unknown>>();

export function memoryGet<T>(key: string, ttlMs: number): T | undefined {
  const entry = store.get(key) as MemoryEntry<T> | undefined;
  if (!entry || entry.value === undefined) return undefined;
  if (Date.now() - entry.at > ttlMs) return undefined;
  return entry.value;
}

export function memoryGetAt(key: string): number | undefined {
  const entry = store.get(key);
  return entry && entry.value !== undefined ? entry.at : undefined;
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

export function memorySet<T>(key: string, value: T): void {
  const current = store.get(key) as MemoryEntry<T> | undefined;
  store.set(key, { value, at: Date.now(), inflight: current?.inflight });
}

export function memoryInvalidate(prefix = ""): void {
  if (!prefix) {
    store.clear();
    return;
  }
  for (const key of [...store.keys()]) {
    if (key.startsWith(prefix)) store.delete(key);
  }
}

export async function memoryLoad<T>(
  key: string,
  loader: () => Promise<T>,
  options: { force?: boolean; ttlMs?: number } = {},
): Promise<T> {
  const ttlMs = options.ttlMs ?? 15_000;
  const existing = store.get(key) as MemoryEntry<T> | undefined;
  if (!options.force && existing?.value !== undefined && Date.now() - existing.at <= ttlMs) {
    return existing.value;
  }
  if (existing?.inflight) {
    try {
      return await existing.inflight;
    } catch (error) {
      // The shared request was cancelled by ITS caller (e.g. an unmounted
      // component). That must not cancel this caller: load independently.
      if (!isAbortError(error)) throw error;
    }
  }

  const inflight = loader()
    .then((value) => {
      store.set(key, { value, at: Date.now() });
      return value;
    })
    .catch((error) => {
      const current = store.get(key) as MemoryEntry<T> | undefined;
      if (current?.inflight === inflight) {
        store.set(key, { value: current?.value, at: current?.at ?? 0 });
      }
      throw error;
    });

  store.set(key, { value: existing?.value, at: existing?.at ?? 0, inflight });
  return inflight;
}
