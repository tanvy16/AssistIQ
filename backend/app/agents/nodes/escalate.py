"""Persist a real support ticket and mark the conversation for human follow-up."""

from __future__ import annotations

import uuid

from app.agents.state import ChatGraphState, get_configurable
from app.models.enums import TicketCategory, TicketPriority
from app.services.ticket_service import TicketError, ensure_ticket_for_conversation


async def escalate(state: ChatGraphState, config) -> ChatGraphState:
    configurable = get_configurable(config)
    db = configurable.get("db")
    actor = configurable.get("actor")
    conversation_id = state.get("conversation_id")
    user_id = state.get("user_id")
    user_message = state.get("user_message") or ""
    reason = state.get("escalation_reason") or "user_requested_human"

    if not db or actor is None or not conversation_id or not user_id:
        return {
            **state,
            "answer": (
                "I could not create a support ticket for human assistance because the request "
                "context is incomplete. Please open a ticket from My tickets."
            ),
            "skip_generation": True,
            "escalation_triggered": False,
            "confidence_state": "NO_EVIDENCE",
            "citations": [],
            "error_message": "ticket_context_unavailable",
        }

    try:
        ticket = await ensure_ticket_for_conversation(
            db,
            actor=actor,
            conversation_id=uuid.UUID(conversation_id),
            requester_id=uuid.UUID(user_id),
            title=(user_message.strip()[:80] or "Human assistance requested"),
            description=(
                f"Escalated from chat conversation {conversation_id}.\n"
                f"Reason: {reason}\n\n"
                f"User request:\n{user_message.strip()}"
            ),
            category=TicketCategory.OTHER,
            priority=TicketPriority.MEDIUM,
        )
    except TicketError:
        return {
            **state,
            "answer": (
                "I could not create a support ticket for human assistance. "
                "Please try Request human again or open a ticket from My tickets."
            ),
            "skip_generation": True,
            "escalation_triggered": False,
            "confidence_state": "NO_EVIDENCE",
            "citations": [],
            "error_message": "ticket_create_failed",
        }

    return {
        **state,
        "answer": (
            f"I've created support ticket {ticket.ticket_number} and requested human assistance. "
            "An agent can pick it up from the queue."
        ),
        "skip_generation": True,
        "escalation_triggered": True,
        "escalation_reason": reason,
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "confidence_state": "NO_EVIDENCE",
        "citations": [],
    }
