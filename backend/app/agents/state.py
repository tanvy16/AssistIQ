"""LangGraph chat workflow state."""

from __future__ import annotations

from typing import Any, TypedDict


class ChatGraphState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    user_message: str
    history: list[dict[str, str]]
    intent: str
    route: str
    retrieved_chunks: list[dict[str, Any]]
    ticket_context: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    answer: str
    confidence_state: str
    escalation_triggered: bool
    escalation_reason: str | None
    selected_model_id: str
    generation_model_id: str
    intent_model_id: str | None
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    top_k: int
    retrieved_count: int
    top_similarity_score: float | None
    generation_usage: dict[str, Any]
    skip_generation: bool
    generation_prompt: str
    error_message: str
    it_request_id: str | None
    password_reset_id: str | None
    ticket_id: str | None
    ticket_number: str | None


def get_configurable(config: Any) -> dict[str, Any]:
    if not config:
        return {}
    if isinstance(config, dict):
        value = config.get("configurable") or {}
        return value if isinstance(value, dict) else {}
    getter = getattr(config, "get", None)
    if callable(getter):
        value = getter("configurable") or {}
        return value if isinstance(value, dict) else {}
    return {}
