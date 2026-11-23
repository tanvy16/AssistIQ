export type KnowledgeDocumentStatus = "draft" | "published" | "archived";

export type KnowledgeCategory =
  | "network"
  | "access"
  | "hardware"
  | "software"
  | "other";

export type KnowledgeDocument = {
  id: string;
  title: string;
  description: string | null;
  body: string;
  category: KnowledgeCategory;
  source: string | null;
  status: KnowledgeDocumentStatus;
  version: number;
  created_by: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocumentListResponse = {
  items: KnowledgeDocument[];
  total: number;
};

export type KnowledgeDocumentInput = {
  title: string;
  description?: string | null;
  body?: string;
  category: KnowledgeCategory;
  source?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type KnowledgeSearchResult = {
  document_id: string;
  chunk_id: string;
  title: string;
  content: string;
  similarity_score: number;
  category: string;
  source: string | null;
  chunk_index: number;
  metadata: Record<string, unknown>;
};

export type KnowledgeSearchResponse = {
  results: KnowledgeSearchResult[];
  total: number;
};
