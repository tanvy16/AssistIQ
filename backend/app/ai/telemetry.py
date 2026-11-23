"""Structured AI inference telemetry persistence and logging."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.enums import AIModelType
from app.ai.schemas import AIInferenceInput, AIInferenceOutput
from app.models.ai import AIInferenceTelemetry

logger = logging.getLogger("assistiq.ai.telemetry")


def _input_size(input_data: dict[str, Any]) -> int:
    text = input_data.get("text")
    if isinstance(text, str):
        return len(text)
    return len(str(input_data))


def _output_size(output: dict[str, Any]) -> int:
    text = output.get("text") or output.get("label") or ""
    return len(str(text))


async def record_inference_telemetry(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    user_id: uuid.UUID | None,
    inference_input: AIInferenceInput,
    inference_output: AIInferenceOutput | None,
    success: bool,
    error_type: str | None = None,
    latency_ms: float | None = None,
) -> AIInferenceTelemetry:
    usage = inference_output.usage if inference_output else None
    model_type = inference_input.model_type
    is_llm = model_type == AIModelType.LLM

    record = AIInferenceTelemetry(
        request_id=request_id,
        user_id=user_id,
        model_registry_id=inference_input.registry_id,
        model_type=model_type,
        provider=inference_input.provider,
        model_name=inference_input.model_name,
        model_key=inference_input.model_key,
        task=(
            inference_input.task.value
            if hasattr(inference_input.task, "value")
            else str(inference_input.task)
        ),
        latency_ms=latency_ms if latency_ms is not None else (inference_output.latency_ms if inference_output else 0.0),
        success=success,
        error_type=error_type,
        input_size=_input_size(inference_input.input_data),
        output_size=_output_size(inference_output.output) if inference_output else 0,
        prompt_tokens=usage.prompt_tokens if is_llm and usage else None,
        completion_tokens=usage.completion_tokens if is_llm and usage else None,
        total_tokens=usage.total_tokens if is_llm and usage else None,
        estimated_cost_usd=usage.estimated_cost_usd if is_llm and usage else None,
        inference_units=usage.inference_units if not is_llm and usage else None,
        telemetry_metadata={"model_key": inference_input.model_key},
    )
    db.add(record)
    await db.flush()

    logger.info(
        "ai_inference",
        extra={
            "request_id": str(request_id),
            "model_type": model_type.value,
            "provider": inference_input.provider,
            "model_name": inference_input.model_name,
            "task": record.task,
            "latency_ms": round(record.latency_ms, 2),
            "success": success,
            "error_type": error_type,
            "input_size": record.input_size,
            "output_size": record.output_size,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "inference_units": record.inference_units,
        },
    )
    return record
