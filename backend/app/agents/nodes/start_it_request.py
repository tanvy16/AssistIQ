"""Create an IT request from a software/access chat intent."""

from __future__ import annotations

import uuid

from app.agents.state import ChatGraphState
from app.services.it_request_service import get_it_request_service


_STATUS_MESSAGES = {
    "completed": (
        "I opened an IT request and completed a simulated catalog action. "
        "No software was installed and no access was changed on any real system."
    ),
    "approval_required": (
        "I created an IT request. Policy requires approval before the simulated action can proceed."
    ),
    "escalated": (
        "I created an IT request, but this needs human review. It was not executed."
    ),
    "rejected": (
        "I created an IT request, but policy denied it because the resource is not an approved catalog item "
        "or the item is disabled."
    ),
    "rolled_back": (
        "The simulated action did not validate and was rolled back. Nothing was changed on your machine."
    ),
}


async def start_it_request(state: ChatGraphState, config) -> ChatGraphState:
    configurable = config.get("configurable", {})
    db = configurable.get("db")
    actor = configurable.get("actor")
    if db is None or actor is None:
        return {
            **state,
            "answer": "I couldn't start an IT request because the workflow is unavailable.",
            "skip_generation": True,
            "citations": [],
        }

    conversation_id = uuid.UUID(state["conversation_id"]) if state.get("conversation_id") else None
    service = get_it_request_service()
    try:
        request = await service.create_request(
            db,
            actor=actor,
            message=state.get("user_message", ""),
            conversation_id=conversation_id,
        )
    except Exception:
        return {
            **state,
            "answer": (
                "I couldn't complete the IT request workflow. The request was not executed. "
                "You can try again from IT Requests or ask for human assistance."
            ),
            "skip_generation": True,
            "citations": [],
        }
    prefix = _STATUS_MESSAGES.get(
        request.status.value,
        "I created an IT request. You can track it in IT Requests.",
    )
    answer = (
        f"{prefix}\n\nRequest ID: {request.id}\n"
        f"Type: {request.request_type.value}\n"
        f"Resource: {request.requested_resource}\n"
        f"Status: {request.status.value}\n"
        f"Risk: {request.risk_level.value}"
    )
    return {
        **state,
        "answer": answer,
        "skip_generation": True,
        "citations": [],
        "confidence_state": "HIGH_CONFIDENCE" if request.status.value == "completed" else "LOW_CONFIDENCE",
        "it_request_id": str(request.id),
        "escalation_triggered": request.status.value == "escalated",
        "escalation_reason": "it_request_policy" if request.status.value == "escalated" else None,
    }
