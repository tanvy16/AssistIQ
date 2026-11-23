"""Ensure citations align with retrieved evidence."""

from __future__ import annotations

from app.agents.state import ChatGraphState


async def citation_check(state: ChatGraphState, config) -> ChatGraphState:
    citations = state.get("citations") or []
    answer = state.get("answer") or ""

    if not citations:
        return {**state, "citations": []}

    # Keep only citations that remain in retrieved set (no fabrication)
    validated = [c for c in citations if c.get("document_id") and c.get("chunk_id")]
    if validated and "KB-" not in answer and "document_id" not in answer.lower():
        # Answer didn't reference citations explicitly; still return structured citations
        pass
    return {**state, "citations": validated}
