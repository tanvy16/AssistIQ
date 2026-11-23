import { describe, expect, it } from "vitest";

import { formatSlaLabel, getSlaState } from "./sla";
import { categoryLabels, statusLabels } from "./ticketLabels";

describe("getSlaState", () => {
  it("marks past due timestamps as overdue", () => {
    const dueAt = new Date(Date.now() - 60_000).toISOString();
    expect(getSlaState(dueAt)).toBe("overdue");
  });

  it("marks near-term due dates as due-soon", () => {
    const dueAt = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
    expect(getSlaState(dueAt)).toBe("due-soon");
  });
});

describe("formatSlaLabel", () => {
  it("returns Overdue for elapsed due times", () => {
    const dueAt = new Date(Date.now() - 60_000).toISOString();
    expect(formatSlaLabel(dueAt)).toBe("Overdue");
  });
});

describe("ticket labels", () => {
  it("includes SDD ticket categories", () => {
    expect(Object.keys(categoryLabels).sort()).toEqual([
      "access",
      "hardware",
      "network",
      "other",
      "software",
    ]);
  });

  it("includes phase 3 ticket statuses", () => {
    expect(Object.keys(statusLabels).sort()).toEqual([
      "closed",
      "in_progress",
      "open",
      "pending",
      "resolved",
    ]);
  });
});
