import { describe, expect, it } from "vitest";

import { confidenceLabel, confidenceTone } from "./chat";
import type { Escalation } from "./chat.types";

describe("chat helpers", () => {
  it("maps confidence states to labels", () => {
    expect(confidenceLabel("HIGH_CONFIDENCE")).toBe("High confidence");
    expect(confidenceLabel("LOW_CONFIDENCE")).toBe("Low confidence");
    expect(confidenceLabel("NO_EVIDENCE")).toBe("Limited evidence");
  });

  it("maps confidence states to badge tones", () => {
    expect(confidenceTone("HIGH_CONFIDENCE")).toBe("ai");
    expect(confidenceTone("LOW_CONFIDENCE")).toBe("default");
    expect(confidenceTone("NO_EVIDENCE")).toBe("muted");
  });

  it("treats escalation ticket fields as optional until persistence returns them", () => {
    const withoutTicket: Escalation = {
      id: "esc-1",
      conversation_id: "conv-1",
      requested_by: "user-1",
      reason: "user_requested_human",
      status: "open",
      notes: null,
      created_at: "2026-10-23T00:00:00Z",
      resolved_at: null,
    };
    expect(withoutTicket.ticket_number ?? null).toBeNull();
    const withTicket = { ...withoutTicket, ticket_number: "TICK-00011", ticket_id: "t-1" };
    expect(withTicket.ticket_number).toBe("TICK-00011");
  });
});
