"""Knowledge base ingestion, lifecycle, and retrieval."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.chroma import ChromaAdapter, ChromaAdapterError, get_chroma_adapter
from app.core.config import Settings, get_settings
from app.models.enums import KnowledgeDocumentStatus, TicketCategory, UserRole
from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.models.user import User
from app.services.chunking_service import TextChunk, chunk_text
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.retrieval_telemetry import RetrievalTelemetry


class KnowledgeError(Exception):
    pass


class KnowledgeNotFoundError(KnowledgeError):
    pass


class KnowledgeAccessDeniedError(KnowledgeError):
    pass


class KnowledgeValidationError(KnowledgeError):
    pass


class KnowledgeStateError(KnowledgeError):
    pass


def _chroma_id_for_chunk(document_id: uuid.UUID, chunk_index: int) -> str:
    return f"{document_id}:{chunk_index}"


class KnowledgeBaseService:
    def __init__(
        self,
        *,
        chroma: ChromaAdapter | None = None,
        embedding: EmbeddingService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._chroma = chroma or get_chroma_adapter()
        self._embedding = embedding or get_embedding_service()

    async def create_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        title: str,
        description: str | None,
        body: str,
        category: TicketCategory,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            title=title.strip(),
            description=description,
            body=body,
            category=category,
            source=source,
            status=KnowledgeDocumentStatus.DRAFT,
            version=1,
            created_by=actor.id,
            doc_metadata=metadata,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        actor: User,
        status: KnowledgeDocumentStatus | None = None,
    ) -> list[KnowledgeDocument]:
        if actor.role == UserRole.ADMIN:
            query = select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())
            if status is not None:
                query = query.where(KnowledgeDocument.status == status)
        else:
            query = (
                select(KnowledgeDocument)
                .where(KnowledgeDocument.status == KnowledgeDocumentStatus.PUBLISHED)
                .order_by(KnowledgeDocument.updated_at.desc())
            )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        document_id: uuid.UUID,
        include_chunks: bool = False,
    ) -> KnowledgeDocument:
        query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        if include_chunks:
            query = query.options(selectinload(KnowledgeDocument.chunks))
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        if document is None:
            raise KnowledgeNotFoundError("Document not found")

        if actor.role != UserRole.ADMIN:
            if document.status != KnowledgeDocumentStatus.PUBLISHED:
                raise KnowledgeAccessDeniedError("Document is not accessible")

        return document

    async def update_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        document_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        body: str | None = None,
        category: TicketCategory | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        document = await self.get_document(db, actor=actor, document_id=document_id)
        if actor.role != UserRole.ADMIN:
            raise KnowledgeAccessDeniedError("Only admins can update documents")
        if document.status == KnowledgeDocumentStatus.ARCHIVED:
            raise KnowledgeStateError("Archived documents cannot be edited")

        if title is not None:
            document.title = title.strip()
        if description is not None:
            document.description = description
        if body is not None:
            document.body = body
        if category is not None:
            document.category = category
        if source is not None:
            document.source = source
        if metadata is not None:
            document.doc_metadata = metadata

        if document.status == KnowledgeDocumentStatus.PUBLISHED and body is not None:
            document.status = KnowledgeDocumentStatus.DRAFT
            document.version += 1
            await self._remove_vectors(db, document)

        await db.commit()
        await db.refresh(document)
        return document

    async def publish_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        document_id: uuid.UUID,
    ) -> KnowledgeDocument:
        document = await self.get_document(
            db, actor=actor, document_id=document_id, include_chunks=True
        )
        if actor.role != UserRole.ADMIN:
            raise KnowledgeAccessDeniedError("Only admins can publish documents")
        if document.status == KnowledgeDocumentStatus.ARCHIVED:
            raise KnowledgeStateError("Archived documents cannot be published")
        if not document.body.strip():
            raise KnowledgeValidationError("Document body is required before publishing")

        await self._remove_vectors(db, document)
        chunks = chunk_text(document.body, settings=self._settings)
        if not chunks:
            raise KnowledgeValidationError("Document body produced no chunks")

        document.status = KnowledgeDocumentStatus.PUBLISHED
        await self._write_chunks(db, document, chunks)
        await db.commit()
        await db.refresh(document)
        return document

    async def archive_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        document_id: uuid.UUID,
    ) -> KnowledgeDocument:
        document = await self.get_document(
            db, actor=actor, document_id=document_id, include_chunks=True
        )
        if actor.role != UserRole.ADMIN:
            raise KnowledgeAccessDeniedError("Only admins can archive documents")

        await self._remove_vectors(db, document)
        document.status = KnowledgeDocumentStatus.ARCHIVED
        await db.commit()
        await db.refresh(document)
        return document

    async def delete_document(
        self,
        db: AsyncSession,
        *,
        actor: User,
        document_id: uuid.UUID,
    ) -> None:
        document = await self.get_document(
            db, actor=actor, document_id=document_id, include_chunks=True
        )
        if actor.role != UserRole.ADMIN:
            raise KnowledgeAccessDeniedError("Only admins can delete documents")

        await self._remove_vectors(db, document)
        await db.delete(document)
        await db.commit()

    async def search_published(
        self,
        db: AsyncSession,
        *,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise KnowledgeValidationError("Query must not be empty")
        if top_k < 1 or top_k > self._settings.RAG_SEARCH_TOP_K_MAX:
            raise KnowledgeValidationError(
                f"top_k must be between 1 and {self._settings.RAG_SEARCH_TOP_K_MAX}"
            )

        started = time.perf_counter()
        query_embedding = self._embedding.embed_query(cleaned_query)

        try:
            hits = await asyncio.to_thread(
                self._chroma.similarity_search,
                query_embedding=query_embedding,
                top_k=top_k,
                where={"status": KnowledgeDocumentStatus.PUBLISHED.value},
            )
        except ChromaAdapterError as exc:
            raise KnowledgeError("Search failed") from exc

        if not hits:
            telemetry = RetrievalTelemetry(
                query=cleaned_query,
                top_k=top_k,
                embedding_model_id=self._embedding.model_id,
                result_count=0,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            telemetry.record()
            return []

        chroma_ids = [hit["chroma_id"] for hit in hits]
        chunk_result = await db.execute(
            select(DocumentChunk, KnowledgeDocument)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .where(
                DocumentChunk.chroma_id.in_(chroma_ids),
                KnowledgeDocument.status == KnowledgeDocumentStatus.PUBLISHED,
            )
        )
        rows = chunk_result.all()
        row_by_chroma = {chunk.chroma_id: (chunk, doc) for chunk, doc in rows}

        results: list[dict[str, Any]] = []
        scores: list[float] = []
        for hit in hits:
            pair = row_by_chroma.get(hit["chroma_id"])
            if pair is None:
                continue
            chunk, doc = pair
            score = hit.get("similarity_score") or 0.0
            scores.append(score)
            results.append(
                {
                    "document_id": doc.id,
                    "chunk_id": chunk.id,
                    "title": doc.title,
                    "content": chunk.content,
                    "similarity_score": score,
                    "category": doc.category.value,
                    "source": doc.source,
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.chunk_metadata or {},
                }
            )

        telemetry = RetrievalTelemetry(
            query=cleaned_query,
            top_k=top_k,
            embedding_model_id=self._embedding.model_id,
            result_count=len(results),
            latency_ms=(time.perf_counter() - started) * 1000,
            similarity_scores=scores,
        )
        telemetry.record()
        return results

    async def _write_chunks(
        self,
        db: AsyncSession,
        document: KnowledgeDocument,
        chunks: list[TextChunk],
    ) -> None:
        embeddings = self._embedding.embed_documents([chunk.content for chunk in chunks])
        chroma_ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for chunk in chunks:
            chroma_id = _chroma_id_for_chunk(document.id, chunk.chunk_index)
            chroma_ids.append(chroma_id)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "document_id": str(document.id),
                    "chunk_index": chunk.chunk_index,
                    "title": document.title,
                    "category": document.category.value,
                    "status": KnowledgeDocumentStatus.PUBLISHED.value,
                }
            )
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    chroma_id=chroma_id,
                    token_count=chunk.token_count,
                    chunk_metadata={"category": document.category.value},
                )
            )

        try:
            await asyncio.to_thread(
                self._chroma.add_chunks,
                ids=chroma_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except ChromaAdapterError:
            await db.rollback()
            raise

    async def _remove_vectors(
        self,
        db: AsyncSession,
        document: KnowledgeDocument,
    ) -> None:
        result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        existing = list(result.scalars().all())
        if not existing:
            return

        chroma_ids = [chunk.chroma_id for chunk in existing]
        try:
            await asyncio.to_thread(self._chroma.delete_chunks, chroma_ids)
        except ChromaAdapterError:
            await db.rollback()
            raise

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )


_knowledge_service: KnowledgeBaseService | None = None


def get_knowledge_service() -> KnowledgeBaseService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeBaseService()
    return _knowledge_service


def reset_knowledge_service() -> None:
    global _knowledge_service
    _knowledge_service = None
