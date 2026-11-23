import type { AIModelType } from "./ai.types";

export const aiModelTypeLabels: Record<AIModelType, string> = {
  lightweight_ml: "Lightweight ML",
  deep_learning: "Deep Learning",
  llm: "LLM",
};

export const aiModelTypeDescriptions: Record<AIModelType, string> = {
  lightweight_ml: "Fast classification and routing with low resource usage.",
  deep_learning: "Semantic NLP tasks using learned representations.",
  llm: "Natural-language generation and complex reasoning tasks.",
};

export const aiModelTypes: AIModelType[] = [
  "lightweight_ml",
  "deep_learning",
  "llm",
];
