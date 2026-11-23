import { describe, expect, it } from "vitest";

import { statusExplanation } from "./itRequests";

describe("IT request status copy", () => {
  it("never claims a real installation occurred", () => {
    const copy = statusExplanation("completed");
    expect(copy.toLowerCase()).toContain("simulation");
    expect(copy.toLowerCase()).not.toContain("has been installed");
  });

  it("explains approval clearly", () => {
    expect(statusExplanation("approval_required")).toMatch(/approval/i);
  });

  it("explains rollback without claiming a real undo on the host", () => {
    expect(statusExplanation("rolled_back").toLowerCase()).toContain("simulated");
  });

  it("explains escalation as human review", () => {
    expect(statusExplanation("escalated").toLowerCase()).toContain("human");
  });
});
