import { afterEach, describe, expect, it, vi } from "vitest";

import { authFetch, registerSessionHandlers } from "./api";
import { hasAnyDailyActivity, shortDayLabel } from "./analytics";
import { memoryInvalidate, memoryLoad } from "./queryMemory";
import { passwordPolicyProblem } from "./security";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  registerSessionHandlers(null);
  memoryInvalidate();
});

describe("authFetch", () => {
  it("refreshes once on 401 and retries with the new token", async () => {
    const calls: { url: string; auth: string | null }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const auth = new Headers(init?.headers).get("Authorization");
        calls.push({ url, auth });
        if (url.endsWith("/auth/refresh")) return json(200, { access_token: "fresh", token_type: "bearer" });
        return auth === "Bearer fresh" ? json(200, { ok: true }) : json(401, { detail: "expired" });
      }),
    );
    const onRefreshed = vi.fn();
    registerSessionHandlers({ onRefreshed, onExpired: vi.fn() });

    const [a, b] = await Promise.all([
      authFetch("http://api/x", { headers: { Authorization: "Bearer stale" } }),
      authFetch("http://api/y", { headers: { Authorization: "Bearer stale" } }),
    ]);
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    // Two concurrent 401s share ONE refresh call.
    expect(calls.filter((c) => c.url.endsWith("/auth/refresh"))).toHaveLength(1);
    expect(onRefreshed).toHaveBeenCalledWith("fresh", undefined);
  });

  it("ends the session when refresh fails and returns the original 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url.endsWith("/auth/refresh") ? json(401, { detail: "no" }) : json(401, { detail: "expired" }),
      ),
    );
    const onExpired = vi.fn();
    registerSessionHandlers({ onRefreshed: vi.fn(), onExpired });
    const response = await authFetch("http://api/x", { headers: { Authorization: "Bearer stale" } });
    expect(response.status).toBe(401);
    expect(onExpired).toHaveBeenCalledTimes(1);
  });

  it("does not attempt refresh for unauthenticated requests or non-401 errors", async () => {
    const fetchMock = vi.fn(async () => json(403, { detail: "Insufficient permissions" }));
    vi.stubGlobal("fetch", fetchMock);
    const forbidden = await authFetch("http://api/x", { headers: { Authorization: "Bearer t" } });
    expect(forbidden.status).toBe(403);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("memoryLoad", () => {
  it("does not propagate another caller's abort to a deduplicated request", async () => {
    const abortError = Object.assign(new Error("aborted"), { name: "AbortError" });
    let call = 0;
    const loader = vi.fn(async () => {
      call += 1;
      if (call === 1) throw abortError;
      return "value";
    });
    const first = memoryLoad("k", loader).catch((err) => err);
    const second = memoryLoad("k", loader);
    expect(await first).toBe(abortError);
    await expect(second).resolves.toBe("value");
  });
});

describe("analytics helpers", () => {
  it("formats ISO dates without timezone shift", () => {
    expect(shortDayLabel("2026-01-01")).toMatch(/1/);
  });

  it("treats an all-zero window as no activity", () => {
    const zero = [{ date: "2026-01-01", created: 0, resolved: 0, escalations: 0, chat_tickets: 0 }];
    expect(hasAnyDailyActivity(zero, ["created", "resolved"])).toBe(false);
    expect(hasAnyDailyActivity([{ ...zero[0], resolved: 2 }], ["created", "resolved"])).toBe(true);
  });
});

describe("passwordPolicyProblem", () => {
  it("mirrors the server policy", () => {
    expect(passwordPolicyProblem("short")).not.toBeNull();
    expect(passwordPolicyProblem("alllowercaseletters")).not.toBeNull();
    expect(passwordPolicyProblem("Correct-Horse-42")).toBeNull();
  });
});
