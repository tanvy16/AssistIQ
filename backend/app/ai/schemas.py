"""Internal AI inference request/response contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.ai.enums import AIModelType, AITaskType


@dataclass
class AIInferenceInput:
    task: AITaskType
    model_type: AIModelType
    provider: str
    model_name: str
    input_data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    registry_id: UUID | None = None
    model_key: str | None = None


@dataclass
class AIUsageMetrics:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    inference_units: int | None = None


@dataclass
class AIInferenceOutput:
    output: dict[str, Any]
    model_type: AIModelType
    provider: str
    model_name: str
    latency_ms: float
    usage: AIUsageMetrics = field(default_factory=AIUsageMetrics)
    registry_id: UUID | None = None
    model_key: str | None = None
