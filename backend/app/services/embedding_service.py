"""Deterministic embedding service abstraction (no LLM)."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.core.config import Settings, get_settings

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


class EmbeddingService(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashEmbeddingService(EmbeddingService):
    """Deterministic hash-based embeddings for Phase 4 retrieval infrastructure."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def model_id(self) -> str:
        return self._settings.EMBEDDING_MODEL_ID

    @property
    def dimension(self) -> int:
        return self._settings.EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        dim = self.dimension
        vector = [0.0] * dim
        normalized = normalize_text(text)
        if not normalized:
            return vector

        tokens = normalized.split()
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for byte_idx, byte_val in enumerate(digest):
                index = (byte_val + byte_idx) % dim
                vector[index] += 1.0 + (byte_val / 255.0)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = HashEmbeddingService()
    return _embedding_service


def reset_embedding_service() -> None:
    global _embedding_service
    _embedding_service = None
