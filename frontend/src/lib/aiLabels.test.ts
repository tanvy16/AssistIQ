import { describe, expect, it } from "vitest";

import { aiModelTypeLabels, aiModelTypes } from "./aiLabels";

describe("aiModelTypes", () => {
  it("defines all three model classes", () => {
    expect(aiModelTypes).toEqual(["lightweight_ml", "deep_learning", "llm"]);
  });

  it("provides labels for each model class", () => {
    expect(aiModelTypeLabels.lightweight_ml).toBe("Lightweight ML");
    expect(aiModelTypeLabels.deep_learning).toBe("Deep Learning");
    expect(aiModelTypeLabels.llm).toBe("LLM");
  });
});
