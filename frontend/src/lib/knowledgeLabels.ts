import type {
  KnowledgeCategory,
  KnowledgeDocumentStatus,
} from "./knowledge.types";

export const knowledgeStatusLabels: Record<KnowledgeDocumentStatus, string> = {
  draft: "Draft",
  published: "Published",
  archived: "Archived",
};

export const knowledgeCategoryLabels: Record<KnowledgeCategory, string> = {
  network: "Network",
  access: "Access",
  hardware: "Hardware",
  software: "Software",
  other: "Other",
};

export const knowledgeCategories = Object.keys(
  knowledgeCategoryLabels,
) as KnowledgeCategory[];
