"""Operational confidence heuristic from retrieval evidence."""

from __future__ import annotations

from app.agents.state import ChatGraphState, get_configurable
from app.core.config import get_settings


async def confidence_check(state: ChatGraphState, config) -> ChatGraphState:
    settings = get_settings()
    citations = state.get("citations") or []
    top_score = state.get("top_similarity_score")

    if not citations or top_score is None:
        confidence = "NO_EVIDENCE"
    elif top_score >= settings.CHAT_CONFIDENCE_HIGH_THRESHOLD and len(citations) >= 1:
        confidence = "HIGH_CONFIDENCE"
    elif top_score >= settings.CHAT_CONFIDENCE_LOW_THRESHOLD:
        confidence = "LOW_CONFIDENCE"
    else:
        confidence = "NO_EVIDENCE"

    configurable = get_configurable(config)
    if configurable.get("defer_generation") and state.get("generation_prompt"):
        return {**state, "confidence_state": confidence}

    answer = state.get("answer") or ""
    if confidence == "NO_EVIDENCE" and state.get("intent") in {"knowledge_query", "general_query"}:
        answer = (
            f"{answer}\n\nNote: I could not find sufficient published knowledge to ground this answer. "
            "Consider requesting human assistance."
        ).strip()

    return {**state, "confidence_state": confidence, "answer": answer}
