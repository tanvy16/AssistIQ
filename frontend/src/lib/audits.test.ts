import { describe, expect, it } from "vitest";

import { fetchAuditEvents } from "./audits";

describe("audits client", () => {
  it("requests the admin audit endpoint", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string) => {
      expect(url).toContain("/api/v1/audits?page=1");
      return {
        ok: true,
        json: async () => ({ items: [], total: 0, page: 1, page_size: 50 }),
      } as Response;
    }) as typeof fetch;
    try {
      const result = await fetchAuditEvents("token");
      expect(result.items).toEqual([]);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
