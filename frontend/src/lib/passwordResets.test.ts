import { describe, expect, it } from "vitest";

import { passwordResetStatusCopy } from "./passwordResets";

describe("password reset status copy", () => {
  it("never claims a real password change on completion", () => {
    const copy = passwordResetStatusCopy("completed");
    expect(copy).toBe("Simulation completed successfully.");
    expect(copy.toLowerCase()).toContain("simulation");
    expect(copy.toLowerCase()).not.toContain("has been changed");
  });

  it("explains verification and confirmation gates", () => {
    expect(passwordResetStatusCopy("verification_required")).toMatch(/email/i);
    expect(passwordResetStatusCopy("confirmation_required")).toMatch(/confirm/i);
  });

  it("explains escalation without claiming success", () => {
    expect(passwordResetStatusCopy("escalated").toLowerCase()).toContain("human");
  });
});
