"""Load recent ticket context for the user."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.agents.state import ChatGraphState
from app.models.ticket import Ticket


async def retrieve_ticket_context(state: ChatGraphState, config) -> ChatGraphState:
    configurable = config.get("configurable", {})
    db = configurable.get("db")
    user_id = uuid.UUID(state["user_id"])

    tickets: list[dict] = []
    if db is not None:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.requester_id == user_id)
            .order_by(Ticket.created_at.desc())
            .limit(5)
        )
        for ticket in result.scalars().all():
            tickets.append(
                {
                    "ticket_id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                }
            )

    return {**state, "ticket_context": tickets}
