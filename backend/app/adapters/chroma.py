"""ChromaDB adapter for vector storage and similarity search."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ChromaAdapterError(Exception):
    """Raised when Chroma operations fail."""


class ChromaAdapter:
    """Encapsulates Chroma persistent client and collection operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: chromadb.PersistentClient | None = None
        self._collection: Collection | None = None

    @property
    def collection_name(self) -> str:
        return self._settings.CHROMA_COLLECTION_NAME

    def _ensure_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            persist_dir = Path(self._settings.CHROMA_PERSIST_DIR)
            try:
                persist_dir.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(persist_dir))
            except OSError as exc:
                raise ChromaAdapterError(
                    "Failed to initialize vector store"
                ) from exc
        return self._client

    def get_collection(self) -> Collection:
        if self._collection is None:
            client = self._ensure_client()
            try:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as exc:
                raise ChromaAdapterError(
                    "Failed to access vector collection"
                ) from exc
        return self._collection

    def add_chunks(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            raise ChromaAdapterError("Chunk batch fields must have equal length")
        try:
            self.get_collection().add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise ChromaAdapterError("Failed to add chunks to vector store") from exc

    def update_chunks(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        try:
            self.get_collection().update(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise ChromaAdapterError("Failed to update chunks in vector store") from exc

    def delete_chunks(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self.get_collection().delete(ids=ids)
        except Exception as exc:
            raise ChromaAdapterError("Failed to delete chunks from vector store") from exc

    def similarity_search(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            result = self.get_collection().query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise ChromaAdapterError("Vector similarity search failed") from exc

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[dict[str, Any]] = []
        for idx, chroma_id in enumerate(ids):
            distance = distances[idx] if idx < len(distances) else None
            similarity = None
            if distance is not None:
                similarity = max(0.0, 1.0 - float(distance))
            hits.append(
                {
                    "chroma_id": chroma_id,
                    "content": documents[idx] if idx < len(documents) else "",
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "similarity_score": similarity,
                }
            )
        return hits

    def reset_collection(self) -> None:
        """Test helper: drop and recreate the collection."""
        client = self._ensure_client()
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None


_chroma_adapter: ChromaAdapter | None = None


def get_chroma_adapter() -> ChromaAdapter:
    global _chroma_adapter
    if _chroma_adapter is None:
        _chroma_adapter = ChromaAdapter()
    return _chroma_adapter


def reset_chroma_adapter() -> None:
    global _chroma_adapter
    _chroma_adapter = None
