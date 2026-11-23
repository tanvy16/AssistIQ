"""Local lightweight ML adapter (Logistic Regression-style keyword scoring)."""

from __future__ import annotations

import re
import time
from typing import Any

from app.ai.adapters.base import BaseModelAdapter, ModelAdapterError
from app.ai.enums import AIModelType, AITaskType
from app.ai.schemas import AIInferenceInput, AIInferenceOutput, AIUsageMetrics

_DEFAULT_LABEL_KEYWORDS: dict[str, list[str]] = {
    "network": ["vpn", "wifi", "network", "dns", "latency", "connection"],
    "access": ["password", "login", "access", "account", "mfa", "sso"],
    "hardware": ["laptop", "monitor", "keyboard", "printer", "hardware", "device"],
    "software": ["install", "application", "software", "update", "license", "crash"],
    "other": ["other", "general", "help"],
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _score_label(tokens: set[str], keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in tokens)
    return hits / len(keywords)


class LightweightMLAdapter(BaseModelAdapter):
    """Deterministic local classifier suitable for ticket routing prototypes."""

    def supports_task(self, task: str) -> bool:
        return task in {
            AITaskType.CLASSIFICATION.value,
            AITaskType.INTENT_DETECTION.value,
            AITaskType.REGRESSION.value,
        }

    async def infer(self, request: AIInferenceInput) -> AIInferenceOutput:
        if not self.supports_task(request.task.value if isinstance(request.task, AITaskType) else request.task):
            raise ModelAdapterError(f"Task not supported by lightweight ML: {request.task}")

        started = time.perf_counter()
        task = (
            request.task
            if isinstance(request.task, AITaskType)
            else AITaskType(request.task)
        )

        if task == AITaskType.REGRESSION:
            output = self._run_regression(request.input_data)
        else:
            output = self._run_classification(request.input_data)

        latency_ms = (time.perf_counter() - started) * 1000
        return AIInferenceOutput(
            output=output,
            model_type=AIModelType.LIGHTWEIGHT_ML,
            provider=request.provider,
            model_name=request.model_name,
            latency_ms=latency_ms,
            usage=AIUsageMetrics(inference_units=output.get("feature_count")),
            registry_id=request.registry_id,
            model_key=request.model_key,
        )

    def _run_classification(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = str(input_data.get("text", "")).strip()
        if not text:
            raise ModelAdapterError("Classification input requires non-empty text")

        labels = input_data.get("labels")
        if labels:
            label_keywords = {str(label): [str(label).lower()] for label in labels}
        else:
            label_keywords = _DEFAULT_LABEL_KEYWORDS

        tokens = _tokenize(text)
        scores = {
            label: _score_label(tokens, keywords)
            for label, keywords in label_keywords.items()
        }
        if not scores or max(scores.values()) <= 0:
            predicted = "other" if "other" in label_keywords else next(iter(label_keywords))
            confidence = 0.1
        else:
            predicted = max(scores, key=scores.get)
            raw = scores[predicted]
            confidence = raw / max(sum(scores.values()), 1e-6)
            confidence = min(1.0, max(0.0, confidence))

        return {
            "label": predicted,
            "confidence": round(confidence, 4),
            "scores": {k: round(v, 4) for k, v in scores.items()},
            "feature_count": len(tokens),
        }

    def _run_regression(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = str(input_data.get("text", ""))
        tokens = _tokenize(text)
        # Simple proxy: more tokens => higher predicted handling minutes (capped)
        value = min(480.0, 15.0 + len(tokens) * 3.5)
        return {
            "value": round(value, 2),
            "feature_count": len(tokens),
        }
