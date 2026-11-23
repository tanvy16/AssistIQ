"""Create a password reset request from chat. Does not execute IAM."""

from __future__ import annotations

import uuid

from app.agents.state import ChatGraphState
from app.services.password_reset_service import get_password_reset_service


async def start_password_reset(state: ChatGraphState, config) -> ChatGraphState:
    configurable = config.get("configurable", {})
    db = configurable.get("db")
    actor = configurable.get("actor")
    if db is None or actor is None:
        return {
            **state,
            "answer": "I couldn't start a password reset because the workflow is unavailable.",
            "skip_generation": True,
            "citations": [],
        }

    conversation_id = uuid.UUID(state["conversation_id"]) if state.get("conversation_id") else None
    service = get_password_reset_service()
    try:
        request = await service.create_request(
            db,
            actor=actor,
            message=state.get("user_message"),
            conversation_id=conversation_id,
        )
    except Exception:
        return {
            **state,
            "answer": (
                "I couldn't open a password reset request. No password was changed. "
                "You can try again from Password Reset or ask for human assistance."
            ),
            "skip_generation": True,
            "citations": [],
        }

    answer = (
        "I opened a secure password reset request. Identity verification is required before anything proceeds. "
        "This is a simulated workflow and does not change your login credentials.\n\n"
        f"Request ID: {request.id}\n"
        f"Status: {request.status.value}\n\n"
        "Next step: open Password Reset, confirm your registered email, then explicitly confirm the simulated reset."
    )
    return {
        **state,
        "answer": answer,
        "skip_generation": True,
        "citations": [],
        "confidence_state": "LOW_CONFIDENCE",
        "password_reset_id": str(request.id),
        "escalation_triggered": False,
    }
