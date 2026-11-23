"""Detect user intent using rules and optional AIModelService."""

from __future__ import annotations

import re
import uuid

from app.agents.intents import ChatIntent
from app.agents.state import ChatGraphState
from app.ai.enums import AITaskType, AIModelType
from app.services.ai_model_service import get_ai_model_service

_KEYWORD_INTENTS: list[tuple[ChatIntent, tuple[str, ...]]] = [
    (ChatIntent.HUMAN_ESCALATION, ("human", "agent", "representative", "escalate", "speak to")),
    (ChatIntent.PASSWORD_RESET_REQUEST, (
        "password reset",
        "reset password",
        "reset my password",
        "forgot password",
        "change password",
    )),
    (
        ChatIntent.SOFTWARE_ACCESS_REQUEST,
        (
            "install software",
            "software access",
            "access request",
            "need access to",
            "give me access",
            "need vscode",
            "need vs code",
            "visual studio code",
            "install python",
            "need python",
            "install git",
            "need git",
            "7-zip",
            "7zip",
            "microsoft visio",
            "microsoft office",
            "need office",
            "finance shared drive",
            "jira",
            "confluence",
            "monitoring dashboard",
            "admin privileges",
            "elevated access",
            "installed",
        ),
    ),
    (ChatIntent.TICKET_CREATION_REQUEST, ("create ticket", "open ticket", "new ticket", "submit ticket")),
    (ChatIntent.TICKET_QUERY, ("my ticket", "ticket status", "ticket #", "ticket number")),
    (ChatIntent.KNOWLEDGE_QUERY, ("how do i", "how to", "guide", "policy", "procedure", "vpn", "wifi")),
]


def _keyword_intent(text: str) -> ChatIntent:
    lowered = text.lower()
    for intent, keywords in _KEYWORD_INTENTS:
        if any(keyword in lowered for keyword in keywords):
            return intent
    if re.search(r"\?", text):
        return ChatIntent.GENERAL_QUERY
    return ChatIntent.KNOWLEDGE_QUERY


async def detect_intent(state: ChatGraphState, config) -> ChatGraphState:
    text = state.get("user_message", "").strip()
    intent = _keyword_intent(text)

    configurable = config.get("configurable", {})
    db = configurable.get("db")
    intent_model_id = state.get("intent_model_id")

    if db is not None and intent_model_id:
        service = get_ai_model_service()
        try:
            result = await service.infer(
                db,
                actor=configurable.get("actor"),
                model_id=uuid.UUID(intent_model_id),
                task=AITaskType.INTENT_DETECTION,
                input_data={"text": text},
                metadata={"conversation_id": state.get("conversation_id")},
                commit=False,
            )
            label = str(result.get("output", {}).get("label", "")).lower()
            label_map = {
                "network": ChatIntent.KNOWLEDGE_QUERY,
                "access": ChatIntent.SOFTWARE_ACCESS_REQUEST,
                "software": ChatIntent.SOFTWARE_ACCESS_REQUEST,
                "hardware": ChatIntent.KNOWLEDGE_QUERY,
                "other": ChatIntent.GENERAL_QUERY,
            }
            if label in label_map and intent == ChatIntent.KNOWLEDGE_QUERY:
                intent = label_map[label]
        except Exception:
            pass

    return {**state, "intent": intent.value}
