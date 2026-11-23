import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.enums import AIModelType, AIEvaluationType
from app.models.base import Base


class AIModelRegistry(Base):
    __tablename__ = "ai_model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_type: Mapped[AIModelType] = mapped_column(
        Enum(
            AIModelType,
            name="ai_model_type",
            native_enum=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capabilities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    config_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AIInferenceTelemetry(Base):
    __tablename__ = "ai_inference_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    model_registry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_model_registry.id", ondelete="SET NULL"),
        index=True,
    )
    model_type: Mapped[AIModelType] = mapped_column(
        Enum(
            AIModelType,
            name="ai_model_type",
            native_enum=True,
            values_callable=lambda values: [value.value for value in values],
            create_type=False,
        ),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telemetry_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AIEvaluationResult(Base):
    __tablename__ = "ai_evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_model_registry.id", ondelete="CASCADE"),
        index=True,
    )
    evaluation_type: Mapped[AIEvaluationType] = mapped_column(
        Enum(
            AIEvaluationType,
            name="ai_evaluation_type",
            native_enum=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dataset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
