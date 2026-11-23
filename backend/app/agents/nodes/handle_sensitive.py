"""Handle sensitive requests without executing workflows."""

from __future__ import annotations

from app.agents.intents import ChatIntent
from app.agents.state import ChatGraphState


async def handle_sensitive_request(state: ChatGraphState, config) -> ChatGraphState:
    intent = state.get("intent")
    if intent == ChatIntent.PASSWORD_RESET_REQUEST.value:
        answer = (
            "Password resets require secure identity verification and cannot be completed in chat. "
            "I can request human assistance to guide you through the approved reset process."
        )
        reason = "sensitive_operation"
    else:
        answer = (
            "This request is treated as a sensitive operation and was not executed. "
            "Password reset remains a later-phase workflow."
        )
        reason = "sensitive_operation"

    return {
        **state,
        "answer": answer,
        "skip_generation": True,
        "confidence_state": "NO_EVIDENCE",
        "escalation_triggered": True,
        "escalation_reason": reason,
        "citations": [],
    }
