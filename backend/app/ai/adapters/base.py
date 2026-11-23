"""Base model adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.schemas import AIInferenceInput, AIInferenceOutput


class ModelAdapterError(Exception):
    """Raised when model inference fails."""


class BaseModelAdapter(ABC):
    @abstractmethod
    async def infer(self, request: AIInferenceInput) -> AIInferenceOutput:
        raise NotImplementedError

    @abstractmethod
    def supports_task(self, task: str) -> bool:
        raise NotImplementedError
