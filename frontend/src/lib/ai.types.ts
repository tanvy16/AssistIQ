export type AIModelType = "lightweight_ml" | "deep_learning" | "llm";

export type AIModel = {
  id: string;
  model_key: string;
  model_type: AIModelType;
  provider: string;
  model_name: string;
  version: number;
  enabled: boolean;
  capabilities: string[] | null;
  config_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type AIModelListResponse = {
  items: AIModel[];
  total: number;
};
