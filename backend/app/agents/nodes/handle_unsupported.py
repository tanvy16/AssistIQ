"""Handle unsupported intents."""

from __future__ import annotations

from app.agents.state import ChatGraphState


async def handle_unsupported(state: ChatGraphState, config) -> ChatGraphState:
    return {
        **state,
        "answer": (
            "I'm not able to help with that request yet. "
            "You can ask about IT knowledge topics, your tickets, or request human assistance."
        ),
        "skip_generation": True,
        "confidence_state": "NO_EVIDENCE",
        "citations": [],
    }
