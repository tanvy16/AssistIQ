export type TimeRangeKey = "24h" | "7d" | "30d" | "custom";

export type LatencyStats = {
  count: number;
  average_ms: number | null;
  min_ms: number | null;
  max_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  p99_ms: number | null;
};

export type NamedCount = {
  name: string;
  count: number;
  extra?: Record<string, unknown> | null;
};

export type TimePoint = {
  bucket: string;
  value: number | null;
  count: number;
};

export type ObservabilitySummary = {
  window: { range: string; start: string; end: string };
  total_ai_requests: number;
  success_rate: number | null;
  average_latency_ms: number | null;
  p95_latency_ms: number | null;
  total_llm_tokens: number | null;
  estimated_cost_usd: number | null;
  cost_label: string;
  escalation_rate: number | null;
  empty: boolean;
};

export type ModelUsageRow = {
  model_key: string | null;
  model_name: string;
  model_type: string;
  provider: string;
  requests: number;
  successful: number;
  failed: number;
  success_rate: number | null;
  average_latency_ms: number | null;
  p95_latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  tokens_unknown_requests: number;
  estimated_cost_usd: number | null;
  cost_unknown_requests: number;
  inference_units: number | null;
};

export type TokenSummary = {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  requests_with_usage: number;
  requests_without_usage: number;
  average_tokens_per_request: number | null;
  by_model: NamedCount[];
  by_task: NamedCount[];
  over_time: TimePoint[];
};

export type CostSummary = {
  label: string;
  total_estimated_usd: number | null;
  requests_with_cost: number;
  requests_without_cost: number;
  average_cost_per_request: number | null;
  by_model: NamedCount[];
  by_task: NamedCount[];
  over_time: TimePoint[];
};

export type EvaluationMetricSet = {
  status: "evaluated" | "Not evaluated";
  metrics: Record<string, unknown> | null;
  dataset_ref: string | null;
  sample_count: number | null;
  evaluated_at: string | null;
};

export type ModelEvaluationRow = {
  model_id: string;
  model_key: string;
  model_name: string;
  model_type: string;
  classification: EvaluationMetricSet;
  regression: EvaluationMetricSet;
  llm_generation: EvaluationMetricSet;
  operational_latency: LatencyStats;
  requests: number;
};

export type RagObservability = {
  retrieval: Record<string, unknown>;
  generation: Record<string, unknown>;
  notes: string;
};

export type ChatObservability = {
  conversations: number;
  messages: number;
  latency: LatencyStats;
  retrieval_latency: LatencyStats;
  generation_latency: LatencyStats;
  average_retrieved_chunks: number | null;
  average_similarity: number | null;
  citation_rate: number | null;
  average_citations: number | null;
  escalation_rate: number | null;
  escalations: number;
  confidence: NamedCount[];
  intents: NamedCount[];
  unsupported_rate: number | null;
};

export type WorkflowObservability = {
  total_requests: number;
  by_type: NamedCount[];
  by_status: NamedCount[];
  by_risk: NamedCount[];
  by_policy: NamedCount[];
  policy_allow_rate: number | null;
  approval_required_rate: number | null;
  denial_rate: number | null;
  escalation_rate: number | null;
  execution_success_rate: number | null;
  validation_success_rate: number | null;
  rollback_rate: number | null;
  stage_latency: Record<string, number | null>;
  execution_mode: string;
};

export type PasswordResetObservability = {
  total_requests: number;
  by_status: NamedCount[];
  by_risk: NamedCount[];
  by_policy: NamedCount[];
  verification_success_rate: number | null;
  verification_failure_rate: number | null;
  confirmation_rate: number | null;
  completion_rate: number | null;
  failure_rate: number | null;
  escalation_rate: number | null;
  stage_latency: Record<string, number | null>;
  execution_mode: string;
};

export type Anomaly = {
  metric: string;
  observed_value: number;
  baseline_value: number | null;
  severity: "warning" | "high" | "critical";
  timestamp: string;
  explanation: string;
};

export type UsageBreakdown = {
  counts: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number | null;
  };
  by_model_type: { name: string; count: number }[];
  by_provider: { name: string; count: number }[];
  by_task: { name: string; count: number }[];
  over_time: TimePoint[];
};

export type LatencyBreakdown = {
  overall: LatencyStats;
  by_model: { name: string; average_ms: number | null; p95_ms: number | null }[];
  over_time: TimePoint[];
};

export type ObservabilityDashboard = {
  summary: ObservabilitySummary;
  models: ModelUsageRow[];
  usage: UsageBreakdown;
  tokens: TokenSummary;
  cost: CostSummary;
  latency: LatencyBreakdown;
  rag: RagObservability;
  chat: ChatObservability;
  itWorkflows: WorkflowObservability;
  passwordResets: PasswordResetObservability;
  evaluations: ModelEvaluationRow[];
  anomalies: Anomaly[];
};
