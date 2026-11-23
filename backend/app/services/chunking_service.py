"""Deterministic text chunking for knowledge ingestion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.services.embedding_service import normalize_text

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    content_hash: str
    token_count: int | None


def compute_content_hash(content: str) -> str:
    normalized = normalize_text(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_input(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip())


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    settings: Settings | None = None,
) -> list[TextChunk]:
    cfg = settings or get_settings()
    size = chunk_size if chunk_size is not None else cfg.RAG_CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else cfg.RAG_CHUNK_OVERLAP

    if size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if overlap >= size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalized = normalize_input(text)
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    text_len = len(normalized)

    while start < text_len:
        end = min(start + size, text_len)
        if end < text_len:
            split_at = normalized.rfind(" ", start, end)
            if split_at > start:
                end = split_at

        content = normalized[start:end].strip()
        if content:
            approx_tokens = max(1, len(content.split()))
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=content,
                    content_hash=compute_content_hash(content),
                    token_count=approx_tokens,
                )
            )
            chunk_index += 1

        if end >= text_len:
            break
        start = max(end - overlap, start + 1)

    return chunks
