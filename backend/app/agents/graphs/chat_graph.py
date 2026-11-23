"""Assemble LangGraph chat workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.citation_check import citation_check
from app.agents.nodes.confidence_check import confidence_check
from app.agents.nodes.detect_intent import detect_intent
from app.agents.nodes.create_support_ticket import create_support_ticket
from app.agents.nodes.escalate import escalate
from app.agents.nodes.generate_answer import generate_answer
from app.agents.nodes.start_it_request import start_it_request
from app.agents.nodes.start_password_reset import start_password_reset
from app.agents.nodes.handle_sensitive import handle_sensitive_request
from app.agents.nodes.handle_unsupported import handle_unsupported
from app.agents.nodes.retrieve_context import retrieve_context
from app.agents.nodes.retrieve_ticket_context import retrieve_ticket_context
from app.agents.nodes.route_request import route_request, route_request_node
from app.agents.nodes.validate_answer import validate_answer
from app.agents.state import ChatGraphState

_chat_graph = None


def build_chat_graph():
    global _chat_graph
    if _chat_graph is not None:
        return _chat_graph

    graph = StateGraph(ChatGraphState)
    graph.add_node("detect_intent", detect_intent)
    graph.add_node("route_request", route_request_node)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("retrieve_ticket_context", retrieve_ticket_context)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("validate_answer", validate_answer)
    graph.add_node("citation_check", citation_check)
    graph.add_node("confidence_check", confidence_check)
    graph.add_node("handle_sensitive_request", handle_sensitive_request)
    graph.add_node("start_it_request", start_it_request)
    graph.add_node("start_password_reset", start_password_reset)
    graph.add_node("handle_unsupported", handle_unsupported)
    graph.add_node("create_support_ticket", create_support_ticket)
    graph.add_node("escalate", escalate)

    graph.add_edge(START, "detect_intent")
    graph.add_edge("detect_intent", "route_request")
    graph.add_conditional_edges(
        "route_request",
        route_request,
        {
            "retrieve_context": "retrieve_context",
            "retrieve_ticket_context": "retrieve_ticket_context",
            "handle_sensitive_request": "handle_sensitive_request",
            "start_it_request": "start_it_request",
            "start_password_reset": "start_password_reset",
            "handle_unsupported": "handle_unsupported",
            "create_support_ticket": "create_support_ticket",
            "escalate": "escalate",
        },
    )

    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("retrieve_ticket_context", "generate_answer")
    graph.add_edge("generate_answer", "validate_answer")
    graph.add_edge("validate_answer", "citation_check")
    graph.add_edge("citation_check", "confidence_check")
    graph.add_edge("confidence_check", END)

    graph.add_edge("handle_sensitive_request", END)
    graph.add_edge("start_it_request", END)
    graph.add_edge("start_password_reset", END)
    graph.add_edge("handle_unsupported", END)
    graph.add_edge("create_support_ticket", END)
    graph.add_edge("escalate", END)

    _chat_graph = graph.compile()
    return _chat_graph


def reset_chat_graph() -> None:
    global _chat_graph
    _chat_graph = None
