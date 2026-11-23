"""Route workflow based on detected intent."""

from __future__ import annotations

from app.agents.intents import INTENT_ROUTE_MAP, ChatIntent
from app.agents.state import ChatGraphState


def route_request(state: ChatGraphState) -> str:
    intent = state.get("intent", ChatIntent.GENERAL_QUERY.value)
    return INTENT_ROUTE_MAP.get(intent, "handle_unsupported")


async def route_request_node(state: ChatGraphState, config) -> ChatGraphState:
    route = route_request(state)
    return {**state, "route": route}
