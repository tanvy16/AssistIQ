"""Provider-agnostic LLM adapter (OpenAI-compatible HTTP API)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.ai.adapters.base import BaseModelAdapter, ModelAdapterError
from app.ai.enums import AIModelType, AITaskType
from app.ai.schemas import AIInferenceInput, AIInferenceOutput, AIUsageMetrics
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_shared_client: httpx.AsyncClient | None = None


def get_llm_http_client(timeout: float) -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(timeout=timeout)
    return _shared_client


async def close_llm_http_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


class LLMAdapter(BaseModelAdapter):
    """OpenAI-compatible chat completions client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def supports_task(self, task: str) -> bool:
        return task in {
            AITaskType.GENERATION.value,
            AITaskType.SUMMARIZATION.value,
            AITaskType.INTENT_DETECTION.value,
            AITaskType.ENTITY_EXTRACTION.value,
            AITaskType.CLASSIFICATION.value,
        }

    async def infer(self, request: AIInferenceInput) -> AIInferenceOutput:
        if not self.supports_task(
            request.task.value if isinstance(request.task, AITaskType) else request.task
        ):
            raise ModelAdapterError(f"Task not supported by LLM adapter: {request.task}")

        if not self._settings.LLM_API_KEY:
            raise ModelAdapterError("LLM provider is not configured")

        prompt = self._build_prompt(request.input_data, request.task)
        started = time.perf_counter()

        payload = self._completion_payload(request, prompt, stream=False)

        headers = {
            "Authorization": f"Bearer {self._settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{self._settings.LLM_BASE_URL.rstrip('/')}/chat/completions"

        try:
            client = get_llm_http_client(self._settings.LLM_TIMEOUT_SECONDS)
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("LLM request failed", extra={"provider": request.provider})
            raise ModelAdapterError("LLM inference failed") from exc

        latency_ms = (time.perf_counter() - started) * 1000
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        usage_raw = data.get("usage") or {}
        prompt_tokens = usage_raw.get("prompt_tokens")
        completion_tokens = usage_raw.get("completion_tokens")
        total_tokens = usage_raw.get("total_tokens")
        estimated_cost = self._estimate_cost(
            request.model_name or self._settings.LLM_DEFAULT_MODEL,
            prompt_tokens,
            completion_tokens,
        )

        return AIInferenceOutput(
            output={"text": content, "finish_reason": data.get("choices", [{}])[0].get("finish_reason")},
            model_type=AIModelType.LLM,
            provider=request.provider,
            model_name=request.model_name,
            latency_ms=latency_ms,
            usage=AIUsageMetrics(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
            ),
            registry_id=request.registry_id,
            model_key=request.model_key,
        )

    async def stream_text(self, request: AIInferenceInput):
        """Yield generated text deltas from the OpenAI-compatible stream."""
        if not self.supports_task(
            request.task.value if isinstance(request.task, AITaskType) else request.task
        ):
            raise ModelAdapterError(f"Task not supported by LLM adapter: {request.task}")
        if not self._settings.LLM_API_KEY:
            raise ModelAdapterError("LLM provider is not configured")

        prompt = self._build_prompt(request.input_data, request.task)
        payload = self._completion_payload(request, prompt, stream=True)
        headers = {
            "Authorization": f"Bearer {self._settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{self._settings.LLM_BASE_URL.rstrip('/')}/chat/completions"

        try:
            client = get_llm_http_client(self._settings.LLM_TIMEOUT_SECONDS)
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            logger.warning("LLM stream failed", extra={"provider": request.provider})
            raise ModelAdapterError("LLM inference failed") from exc

    def _completion_payload(
        self,
        request: AIInferenceInput,
        prompt: str,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model_name or self._settings.LLM_DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": self._settings.LLM_MAX_TOKENS,
            "stream": stream,
        }
        if self._settings.LLM_PROVIDER.lower() == "ollama":
            payload["keep_alive"] = "30m"
        return payload

    def _build_prompt(self, input_data: dict[str, Any], task: Any) -> str:
        text = str(input_data.get("text", "")).strip()
        if not text:
            raise ModelAdapterError("LLM input requires non-empty text")
        task_val = task.value if isinstance(task, AITaskType) else str(task)
        instruction = input_data.get("instruction") or f"Complete the following {task_val} task."
        return f"{instruction}\n\nInput:\n{text}"

    def _estimate_cost(
        self,
        model_name: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> float | None:
        if prompt_tokens is None or completion_tokens is None:
            return None
        pricing = self._settings.llm_pricing_for(
            model_name or self._settings.LLM_DEFAULT_MODEL
        )
        if pricing is None:
            return None
        input_rate, output_rate = pricing
        return round(
            (prompt_tokens / 1000.0) * input_rate + (completion_tokens / 1000.0) * output_rate,
            6,
        )
