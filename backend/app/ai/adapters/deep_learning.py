"""Local deep-learning adapter (dense embedding + softmax scoring)."""

from __future__ import annotations

import math
import time
from typing import Any

from app.ai.adapters.base import BaseModelAdapter, ModelAdapterError
from app.ai.enums import AIModelType, AITaskType
from app.ai.schemas import AIInferenceInput, AIInferenceOutput, AIUsageMetrics
from app.services.embedding_service import HashEmbeddingService, normalize_text


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    max_val = max(values)
    exps = [math.exp(v - max_val) for v in values]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


class DeepLearningAdapter(BaseModelAdapter):
    """Minimal local neural-style classifier using hash embeddings."""

    def __init__(self) -> None:
        self._embedder = HashEmbeddingService()

    def supports_task(self, task: str) -> bool:
        return task in {
            AITaskType.CLASSIFICATION.value,
            AITaskType.INTENT_DETECTION.value,
        }

    async def infer(self, request: AIInferenceInput) -> AIInferenceOutput:
        if not self.supports_task(
            request.task.value if isinstance(request.task, AITaskType) else request.task
        ):
            raise ModelAdapterError(f"Task not supported by deep learning adapter: {request.task}")

        started = time.perf_counter()
        text = str(request.input_data.get("text", "")).strip()
        if not text:
            raise ModelAdapterError("Classification input requires non-empty text")

        labels = request.input_data.get("labels") or [
            "network",
            "access",
            "hardware",
            "software",
            "other",
        ]
        labels = [str(label) for label in labels]

        query_vec = self._embedder.embed_query(normalize_text(text))
        scores: list[float] = []
        for label in labels:
            label_vec = self._embedder.embed_query(normalize_text(label))
            dot = sum(a * b for a, b in zip(query_vec, label_vec))
            scores.append(dot)

        probs = _softmax(scores)
        best_idx = max(range(len(labels)), key=lambda i: probs[i])
        latency_ms = (time.perf_counter() - started) * 1000

        return AIInferenceOutput(
            output={
                "label": labels[best_idx],
                "confidence": round(probs[best_idx], 4),
                "probabilities": {
                    label: round(prob, 4) for label, prob in zip(labels, probs)
                },
                "embedding_dim": len(query_vec),
            },
            model_type=AIModelType.DEEP_LEARNING,
            provider=request.provider,
            model_name=request.model_name,
            latency_ms=latency_ms,
            usage=AIUsageMetrics(inference_units=len(query_vec)),
            registry_id=request.registry_id,
            model_key=request.model_key,
        )
