"""Retrieve published knowledge chunks via Phase 4 service."""

from __future__ import annotations

import time

from app.agents.state import ChatGraphState, get_configurable
from app.core.config import get_settings
from app.services.knowledge_base_service import KnowledgeError, get_knowledge_service


async def retrieve_context(state: ChatGraphState, config) -> ChatGraphState:
    configurable = get_configurable(config)
    db = configurable.get("db")
    settings = get_settings()
    top_k = state.get("top_k") or settings.CHAT_RETRIEVAL_TOP_K
    started = time.perf_counter()

    chunks: list[dict] = []
    if db is not None:
        kb = get_knowledge_service()
        try:
            chunks = await kb.search_published(db, query=state.get("user_message", ""), top_k=top_k)
        except KnowledgeError:
            chunks = []

    latency = (time.perf_counter() - started) * 1000
    citations = [
        {
            "document_id": str(chunk["document_id"]),
            "chunk_id": str(chunk["chunk_id"]),
            "title": chunk["title"],
            "similarity_score": chunk["similarity_score"],
            "content": chunk["content"],
            "category": chunk.get("category"),
        }
        for chunk in chunks
    ]
    top_score = citations[0]["similarity_score"] if citations else None

    return {
        **state,
        "retrieved_chunks": chunks,
        "citations": citations,
        "retrieval_latency_ms": latency,
        "retrieved_count": len(chunks),
        "top_similarity_score": top_score,
        "top_k": top_k,
    }
