"""Observability query schemas. Aggregates only — no raw prompts or secrets."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

NOT_EVALUATED = "Not evaluated"


class TimeWindow(BaseModel):
    range: str
    start: datetime
    end: datetime


class LatencyStats(BaseModel):
    count: int = 0
    average_ms: float | None = None
    min_ms: float | None = None
    max_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


class CountRate(BaseModel):
    total: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float | None = None


class NamedCount(BaseModel):
    name: str
    count: int
    extra: dict[str, Any] | None = None


class TimePoint(BaseModel):
    bucket: datetime
    value: float | None = None
    count: int = 0


class ModelUsageRow(BaseModel):
    model_key: str | None
    model_name: str
    model_type: str
    provider: str
    requests: int
    successful: int
    failed: int
    success_rate: float | None
    average_latency_ms: float | None
    p95_latency_ms: float | None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    tokens_unknown_requests: int = 0
    estimated_cost_usd: float | None = None
    cost_unknown_requests: int = 0
    inference_units: int | None = None


class TokenSummary(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    requests_with_usage: int = 0
    requests_without_usage: int = 0
    average_tokens_per_request: float | None = None
    by_model: list[NamedCount] = Field(default_factory=list)
    by_task: list[NamedCount] = Field(default_factory=list)
    over_time: list[TimePoint] = Field(default_factory=list)


class CostSummary(BaseModel):
    label: str = "Estimated Cost"
    total_estimated_usd: float | None = None
    requests_with_cost: int = 0
    requests_without_cost: int = 0
    average_cost_per_request: float | None = None
    by_model: list[NamedCount] = Field(default_factory=list)
    by_task: list[NamedCount] = Field(default_factory=list)
    over_time: list[TimePoint] = Field(default_factory=list)


class EvaluationMetricSet(BaseModel):
    status: Literal["evaluated", "Not evaluated"]
    metrics: dict[str, Any] | None = None
    dataset_ref: str | None = None
    sample_count: int | None = None
    evaluated_at: datetime | None = None


class ModelEvaluationRow(BaseModel):
    model_id: str
    model_key: str
    model_name: str
    model_type: str
    classification: EvaluationMetricSet
    regression: EvaluationMetricSet
    llm_generation: EvaluationMetricSet
    operational_latency: LatencyStats
    requests: int


class RagObservability(BaseModel):
    retrieval: dict[str, Any]
    generation: dict[str, Any]
    notes: str


class ChatObservability(BaseModel):
    conversations: int = 0
    messages: int = 0
    latency: LatencyStats
    retrieval_latency: LatencyStats
    generation_latency: LatencyStats
    average_retrieved_chunks: float | None = None
    average_similarity: float | None = None
    citation_rate: float | None = None
    average_citations: float | None = None
    escalation_rate: float | None = None
    escalations: int = 0
    confidence: list[NamedCount] = Field(default_factory=list)
    intents: list[NamedCount] = Field(default_factory=list)
    unsupported_rate: float | None = None


class WorkflowObservability(BaseModel):
    total_requests: int = 0
    by_type: list[NamedCount] = Field(default_factory=list)
    by_status: list[NamedCount] = Field(default_factory=list)
    by_risk: list[NamedCount] = Field(default_factory=list)
    by_policy: list[NamedCount] = Field(default_factory=list)
    policy_allow_rate: float | None = None
    approval_required_rate: float | None = None
    denial_rate: float | None = None
    escalation_rate: float | None = None
    execution_success_rate: float | None = None
    validation_success_rate: float | None = None
    rollback_rate: float | None = None
    stage_latency: dict[str, float | None] = Field(default_factory=dict)
    execution_mode: str


class PasswordResetObservability(BaseModel):
    total_requests: int = 0
    by_status: list[NamedCount] = Field(default_factory=list)
    by_risk: list[NamedCount] = Field(default_factory=list)
    by_policy: list[NamedCount] = Field(default_factory=list)
    verification_success_rate: float | None = None
    verification_failure_rate: float | None = None
    confirmation_rate: float | None = None
    completion_rate: float | None = None
    failure_rate: float | None = None
    escalation_rate: float | None = None
    stage_latency: dict[str, float | None] = Field(default_factory=dict)
    execution_mode: str = "IAM execution is simulated using Mock IAM."


class Anomaly(BaseModel):
    metric: str
    observed_value: float
    baseline_value: float | None
    severity: Literal["warning", "high", "critical"]
    timestamp: datetime
    explanation: str


class ObservabilitySummary(BaseModel):
    window: TimeWindow
    total_ai_requests: int = 0
    success_rate: float | None = None
    average_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    total_llm_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_label: str = "Estimated Cost"
    escalation_rate: float | None = None
    empty: bool = True
