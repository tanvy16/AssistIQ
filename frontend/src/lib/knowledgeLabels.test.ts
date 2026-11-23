import { describe, expect, it } from "vitest";

import {
  knowledgeCategoryLabels,
  knowledgeStatusLabels,
} from "./knowledgeLabels";

describe("knowledgeLabels", () => {
  it("defines human-readable status labels", () => {
    expect(knowledgeStatusLabels.draft).toBe("Draft");
    expect(knowledgeStatusLabels.published).toBe("Published");
    expect(knowledgeStatusLabels.archived).toBe("Archived");
  });

  it("defines category labels for all ticket-aligned categories", () => {
    expect(Object.keys(knowledgeCategoryLabels).sort()).toEqual([
      "access",
      "hardware",
      "network",
      "other",
      "software",
    ]);
  });
});
