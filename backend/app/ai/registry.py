"""Resolve adapters for registered AI models."""

from __future__ import annotations

from app.ai.adapters.base import BaseModelAdapter, ModelAdapterError
from app.ai.adapters.deep_learning import DeepLearningAdapter
from app.ai.adapters.lightweight_ml import LightweightMLAdapter
from app.ai.adapters.llm import LLMAdapter
from app.ai.enums import AIModelType
from app.core.config import Settings, get_settings


class AdapterFactory:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._lightweight = LightweightMLAdapter()
        self._deep_learning = DeepLearningAdapter()
        self._llm = LLMAdapter(self._settings)

    def get_adapter(self, model_type: AIModelType) -> BaseModelAdapter:
        if model_type == AIModelType.LIGHTWEIGHT_ML:
            return self._lightweight
        if model_type == AIModelType.DEEP_LEARNING:
            return self._deep_learning
        if model_type == AIModelType.LLM:
            return self._llm
        raise ModelAdapterError(f"Unsupported model type: {model_type}")


_adapter_factory: AdapterFactory | None = None


def get_adapter_factory() -> AdapterFactory:
    global _adapter_factory
    if _adapter_factory is None:
        _adapter_factory = AdapterFactory()
    return _adapter_factory


def reset_adapter_factory() -> None:
    global _adapter_factory
    _adapter_factory = None
