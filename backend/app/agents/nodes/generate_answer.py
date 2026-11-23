"""Generate assistant answer via AIModelService (LLM only)."""

from __future__ import annotations

import time
import uuid

from app.agents.prompts import build_generation_prompt
from app.agents.state import ChatGraphState, get_configurable
from app.ai.enums import AITaskType
from app.services.ai_model_service import AIModelValidationError, get_ai_model_service


async def generate_answer(state: ChatGraphState, config) -> ChatGraphState:
    if state.get("skip_generation"):
        return state

    configurable = get_configurable(config)
    db = configurable.get("db")
    actor = configurable.get("actor")
    generation_model_id = state.get("generation_model_id")

    if not db or not generation_model_id:
        return {
            **state,
            "answer": state.get("answer")
            or "I'm unable to generate a response right now. Please try again or request human assistance.",
            "error_message": "Generation model unavailable",
        }

    prompt = build_generation_prompt(
        user_message=state.get("user_message", ""),
        history=state.get("history", []),
        knowledge_context=state.get("citations", []),
        ticket_context=state.get("ticket_context"),
    )

    if configurable.get("defer_generation"):
        return {
            **state,
            "generation_prompt": prompt,
        }

    started = time.perf_counter()
    try:
        result = await get_ai_model_service().infer(
            db,
            actor=actor,
            model_id=uuid.UUID(generation_model_id),
            task=AITaskType.GENERATION,
            input_data={"text": prompt, "instruction": "Answer the IT support question using retrieved DATA only."},
            metadata={"conversation_id": state.get("conversation_id"), "intent": state.get("intent")},
            commit=False,
        )
    except AIModelValidationError as exc:
        return {
            **state,
            "answer": (
                "I couldn't generate a response with the selected model. "
                "Please verify an enabled LLM is configured or request human assistance."
            ),
            "error_message": str(exc),
            "generation_latency_ms": (time.perf_counter() - started) * 1000,
        }

    latency = (time.perf_counter() - started) * 1000
    answer = str(result.get("output", {}).get("text", "")).strip()
    return {
        **state,
        "answer": answer,
        "generation_latency_ms": latency,
        "generation_usage": result.get("usage", {}),
    }
