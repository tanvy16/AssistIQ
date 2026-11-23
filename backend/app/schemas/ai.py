from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.enums import AIEvaluationType, AIModelType, AITaskType


class AIModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_key: str
    model_type: AIModelType
    provider: str
    model_name: str
    version: int
    enabled: bool
    capabilities: list[str] | None
    config_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AIModelListResponse(BaseModel):
    items: list[AIModelResponse]
    total: int


class AIModelUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class AIInferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: UUID
    task: AITaskType
    input: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None

    @field_validator("input")
    @classmethod
    def validate_input_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("input must not be empty")
        text = value.get("text")
        if isinstance(text, str) and len(text) > 20000:
            raise ValueError("input.text must be at most 20000 characters")
        return value


class AIInferUsageResponse(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    inference_units: int | None = None


class AIInferResponse(BaseModel):
    request_id: UUID
    output: dict[str, Any]
    model_type: AIModelType
    model_id: UUID
    provider: str
    model_name: str
    latency_ms: float
    usage: AIInferUsageResponse


class AIEvaluationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_type: AIEvaluationType
    metrics: dict[str, Any]
    dataset_ref: str | None = None
    sample_count: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=2000)


class AIEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_registry_id: UUID
    evaluation_type: AIEvaluationType
    metrics: dict[str, Any]
    dataset_ref: str | None
    sample_count: int | None
    notes: str | None
    evaluated_at: datetime
    created_at: datetime
