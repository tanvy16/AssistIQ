import { describe, expect, it } from "vitest";

import { memoryGet, memoryInvalidate, memoryLoad, memorySet } from "./queryMemory";

describe("query memory", () => {
  it("returns cached values within ttl and shares in-flight loaders", async () => {
    memoryInvalidate();
    memorySet("dash", { n: 1 });
    expect(memoryGet<{ n: number }>("dash", 10_000)).toEqual({ n: 1 });
    expect(memoryGet<{ n: number }>("dash", 0)).toBeUndefined();

    let calls = 0;
    const loader = () => {
      calls += 1;
      return Promise.resolve({ n: 2 });
    };
    const [a, b] = await Promise.all([
      memoryLoad("obs", loader, { ttlMs: 10_000 }),
      memoryLoad("obs", loader, { ttlMs: 10_000 }),
    ]);
    expect(a).toEqual({ n: 2 });
    expect(b).toEqual({ n: 2 });
    expect(calls).toBe(1);
    memoryInvalidate("obs");
    expect(memoryGet("obs", 10_000)).toBeUndefined();
  });
});
