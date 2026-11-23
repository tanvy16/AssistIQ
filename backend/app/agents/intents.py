"""Chat intent constants."""

from enum import Enum


class ChatIntent(str, Enum):
    KNOWLEDGE_QUERY = "knowledge_query"
    TICKET_QUERY = "ticket_query"
    TICKET_CREATION_REQUEST = "ticket_creation_request"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    SOFTWARE_ACCESS_REQUEST = "software_access_request"
    GENERAL_QUERY = "general_query"
    HUMAN_ESCALATION = "human_escalation"
    UNSUPPORTED = "unsupported"


INTENT_ROUTE_MAP = {
    ChatIntent.KNOWLEDGE_QUERY.value: "retrieve_context",
    ChatIntent.TICKET_QUERY.value: "retrieve_ticket_context",
    ChatIntent.TICKET_CREATION_REQUEST.value: "create_support_ticket",
    ChatIntent.GENERAL_QUERY.value: "retrieve_context",
    ChatIntent.PASSWORD_RESET_REQUEST.value: "start_password_reset",
    ChatIntent.SOFTWARE_ACCESS_REQUEST.value: "start_it_request",
    ChatIntent.HUMAN_ESCALATION.value: "escalate",
    ChatIntent.UNSUPPORTED.value: "handle_unsupported",
}
