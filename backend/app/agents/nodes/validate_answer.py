"""Validate generated answer basics."""

from __future__ import annotations

from app.agents.state import ChatGraphState, get_configurable


async def validate_answer(state: ChatGraphState, config) -> ChatGraphState:
    configurable = get_configurable(config)
    if configurable.get("defer_generation") and state.get("generation_prompt"):
        return state

    answer = (state.get("answer") or "").strip()
    if not answer:
        return {
            **state,
            "answer": (
                "I don't have enough information to provide a reliable answer. "
                "You can request human assistance for further help."
            ),
            "confidence_state": "NO_EVIDENCE",
        }
    return state
