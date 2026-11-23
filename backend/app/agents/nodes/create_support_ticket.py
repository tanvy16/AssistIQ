"""Persist a real support ticket from chat ticket-creation intent."""

from __future__ import annotations

import uuid

from app.agents.state import ChatGraphState, get_configurable
from app.models.enums import TicketCategory, TicketPriority
from app.services.ticket_service import TicketError, ensure_ticket_for_conversation


def _ticket_title(message: str) -> str:
    cleaned = (message or "").strip()
    if not cleaned:
        return "Chat support request"
    return cleaned[:80]


async def create_support_ticket(state: ChatGraphState, config) -> ChatGraphState:
    configurable = get_configurable(config)
    db = configurable.get("db")
    actor = configurable.get("actor")
    conversation_id = state.get("conversation_id")
    user_id = state.get("user_id")
    user_message = state.get("user_message") or ""

    if not db or actor is None or not conversation_id or not user_id:
        return {
            **state,
            "answer": (
                "I could not create a support ticket because the request context is incomplete. "
                "Please open a ticket from My tickets, or try Request human again."
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
            title=_ticket_title(user_message),
            description=(
                f"Created from chat conversation {conversation_id}.\n\n"
                f"User request:\n{user_message.strip()}"
            ),
            category=TicketCategory.OTHER,
            priority=TicketPriority.MEDIUM,
        )
    except TicketError:
        return {
            **state,
            "answer": (
                "I could not create a support ticket right now. "
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
            f"I've created support ticket {ticket.ticket_number}. "
            "You can track it under My tickets."
        ),
        "skip_generation": True,
        "escalation_triggered": False,
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "confidence_state": "NO_EVIDENCE",
        "citations": [],
    }
