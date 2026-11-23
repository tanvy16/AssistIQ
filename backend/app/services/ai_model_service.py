"""AI model orchestration service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.base import ModelAdapterError
from app.ai.enums import AIModelType, AIEvaluationType, AITaskType
from app.ai.registry import get_adapter_factory
from app.ai.schemas import AIInferenceInput, AIInferenceOutput, AIUsageMetrics
from app.ai.telemetry import record_inference_telemetry
from app.models.ai import AIEvaluationResult, AIModelRegistry
from app.models.user import User


class AIServiceError(Exception):
    pass


class AIModelNotFoundError(AIServiceError):
    pass


class AIModelDisabledError(AIServiceError):
    pass


class AIModelValidationError(AIServiceError):
    pass


class AIModelService:
    async def list_models(
        self,
        db: AsyncSession,
        *,
        include_disabled: bool = False,
    ) -> list[AIModelRegistry]:
        query = select(AIModelRegistry).order_by(AIModelRegistry.model_type, AIModelRegistry.model_key)
        if not include_disabled:
            query = query.where(AIModelRegistry.enabled.is_(True))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_model(
        self,
        db: AsyncSession,
        model_id: uuid.UUID,
        *,
        allow_disabled: bool = False,
    ) -> AIModelRegistry:
        result = await db.execute(
            select(AIModelRegistry).where(AIModelRegistry.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise AIModelNotFoundError("Model not found")
        if not model.enabled and not allow_disabled:
            raise AIModelDisabledError("Model is disabled")
        return model

    async def set_model_enabled(
        self,
        db: AsyncSession,
        *,
        model_id: uuid.UUID,
        enabled: bool,
    ) -> AIModelRegistry:
        model = await self.get_model(db, model_id, allow_disabled=True)
        model.enabled = enabled
        await db.commit()
        await db.refresh(model)
        return model

    async def infer(
        self,
        db: AsyncSession,
        *,
        actor: User | None,
        model_id: uuid.UUID,
        task: AITaskType,
        input_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        registry_entry = await self.get_model(db, model_id)
        self._validate_task_for_model(registry_entry, task)

        inference_input = AIInferenceInput(
            task=task,
            model_type=registry_entry.model_type,
            provider=registry_entry.provider,
            model_name=registry_entry.model_name,
            input_data=input_data,
            metadata=metadata or {},
            registry_id=registry_entry.id,
            model_key=registry_entry.model_key,
        )

        request_id = uuid.uuid4()
        adapter = get_adapter_factory().get_adapter(registry_entry.model_type)

        try:
            output = await adapter.infer(inference_input)
            await record_inference_telemetry(
                db,
                request_id=request_id,
                user_id=actor.id if actor else None,
                inference_input=inference_input,
                inference_output=output,
                success=True,
            )
            if commit:
                await db.commit()
            else:
                await db.flush()
            return {
                "request_id": str(request_id),
                "output": output.output,
                "model_type": output.model_type.value,
                "model_id": str(registry_entry.id),
                "provider": output.provider,
                "model_name": output.model_name,
                "latency_ms": round(output.latency_ms, 2),
                "usage": {
                    "prompt_tokens": output.usage.prompt_tokens,
                    "completion_tokens": output.usage.completion_tokens,
                    "total_tokens": output.usage.total_tokens,
                    "estimated_cost_usd": output.usage.estimated_cost_usd,
                    "inference_units": output.usage.inference_units,
                },
            }
        except (ModelAdapterError, ValueError) as exc:
            await record_inference_telemetry(
                db,
                request_id=request_id,
                user_id=actor.id if actor else None,
                inference_input=inference_input,
                inference_output=None,
                success=False,
                error_type=type(exc).__name__,
            )
            if commit:
                await db.commit()
            else:
                await db.flush()
            raise AIModelValidationError(str(exc)) from exc

    async def stream_text(
        self,
        db: AsyncSession,
        *,
        actor: User | None,
        model_id: uuid.UUID,
        task: AITaskType,
        input_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ):
        """Yield text deltas, then persist inference telemetry for the completed stream."""
        import time

        registry_entry = await self.get_model(db, model_id)
        self._validate_task_for_model(registry_entry, task)
        inference_input = AIInferenceInput(
            task=task,
            model_type=registry_entry.model_type,
            provider=registry_entry.provider,
            model_name=registry_entry.model_name,
            input_data=input_data,
            metadata=metadata or {},
            registry_id=registry_entry.id,
            model_key=registry_entry.model_key,
        )
        request_id = uuid.uuid4()
        adapter = get_adapter_factory().get_adapter(registry_entry.model_type)
        stream_fn = getattr(adapter, "stream_text", None)
        if stream_fn is None:
            raise AIModelValidationError("Selected model does not support streaming")

        started = time.perf_counter()
        pieces: list[str] = []
        try:
            async for delta in stream_fn(inference_input):
                pieces.append(delta)
                yield delta
            text = "".join(pieces)
            latency_ms = (time.perf_counter() - started) * 1000
            output = AIInferenceOutput(
                output={"text": text, "finish_reason": "stop"},
                model_type=registry_entry.model_type,
                provider=registry_entry.provider,
                model_name=registry_entry.model_name,
                latency_ms=latency_ms,
                usage=AIUsageMetrics(),
                registry_id=registry_entry.id,
                model_key=registry_entry.model_key,
            )
            await record_inference_telemetry(
                db,
                request_id=request_id,
                user_id=actor.id if actor else None,
                inference_input=inference_input,
                inference_output=output,
                success=True,
            )
            await db.flush()
        except (ModelAdapterError, ValueError) as exc:
            await record_inference_telemetry(
                db,
                request_id=request_id,
                user_id=actor.id if actor else None,
                inference_input=inference_input,
                inference_output=None,
                success=False,
                error_type=type(exc).__name__,
            )
            await db.flush()
            raise AIModelValidationError(str(exc)) from exc

    async def record_evaluation(
        self,
        db: AsyncSession,
        *,
        model_id: uuid.UUID,
        evaluation_type: AIEvaluationType,
        metrics: dict[str, Any],
        dataset_ref: str | None = None,
        sample_count: int | None = None,
        notes: str | None = None,
    ) -> AIEvaluationResult:
        model = await self.get_model(db, model_id, allow_disabled=True)
        self._validate_evaluation_metrics(evaluation_type, metrics)

        record = AIEvaluationResult(
            model_registry_id=model.id,
            evaluation_type=evaluation_type,
            metrics=metrics,
            dataset_ref=dataset_ref,
            sample_count=sample_count,
            notes=notes,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    def _validate_task_for_model(self, model: AIModelRegistry, task: AITaskType) -> None:
        if model.capabilities and task.value not in model.capabilities:
            raise AIModelValidationError(
                f"Model '{model.model_key}' does not support task '{task.value}'"
            )
        adapter = get_adapter_factory().get_adapter(model.model_type)
        if not adapter.supports_task(task.value):
            raise AIModelValidationError(
                f"Adapter for {model.model_type.value} does not support task '{task.value}'"
            )

    def _validate_evaluation_metrics(
        self,
        evaluation_type: AIEvaluationType,
        metrics: dict[str, Any],
    ) -> None:
        if not metrics:
            raise AIModelValidationError("Evaluation metrics must not be empty")

        if evaluation_type == AIEvaluationType.CLASSIFICATION:
            allowed = {
                "accuracy",
                "precision",
                "recall",
                "f1_score",
                "roc_auc",
                "pr_auc",
                "confusion_matrix",
                "latency_ms",
            }
            if not allowed.intersection(metrics.keys()):
                raise AIModelValidationError(
                    "Classification evaluation requires at least one valid metric "
                    "(accuracy, precision, recall, f1_score, etc.)"
                )
        elif evaluation_type == AIEvaluationType.REGRESSION:
            allowed = {"mae", "mse", "rmse", "r2", "latency_ms"}
            if not allowed.intersection(metrics.keys()):
                raise AIModelValidationError(
                    "Regression evaluation requires at least one valid metric (mae, mse, rmse, r2)"
                )
        elif evaluation_type == AIEvaluationType.LLM_GENERATION:
            allowed = {
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "estimated_cost_usd",
                "groundedness",
                "relevance",
                "citation_correctness",
                "faithfulness",
            }
            if not allowed.intersection(metrics.keys()):
                raise AIModelValidationError(
                    "LLM evaluation requires at least one valid LLM metric"
                )


_ai_model_service: AIModelService | None = None


def get_ai_model_service() -> AIModelService:
    global _ai_model_service
    if _ai_model_service is None:
        _ai_model_service = AIModelService()
    return _ai_model_service


def reset_ai_model_service() -> None:
    global _ai_model_service
    _ai_model_service = None
