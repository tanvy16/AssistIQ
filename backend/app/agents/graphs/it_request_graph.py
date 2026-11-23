"""IT request LangGraph — policy and planning only; persistence lives in ITRequestService."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.it_state import ITGraphState
from app.models.it_request import ITPolicyDecision, ITRequestType, ITRiskLevel
from app.services.entity_extraction import CatalogMatch, extract_entities
from app.services.planner_service import build_plan
from app.services.policy_service import PolicyInput, evaluate_policy


def extract_entities_node(state: ITGraphState) -> ITGraphState:
    catalog = [CatalogMatch(**item) for item in state.get("extraction", {}).get("catalog", [])]
    result = extract_entities(state.get("user_message", ""), catalog)
    return {
        **state,
        "request_type": result.request_type.value,
        "resource": result.resource,
        "extraction": result.model_dump(),
    }


def policy_check_node(state: ITGraphState) -> ITGraphState:
    extraction = state.get("extraction") or {}
    catalog_risk = ITRiskLevel(extraction["catalog_risk"]) if extraction.get("catalog_risk") else None
    policy = evaluate_policy(
        PolicyInput(
            request_type=ITRequestType(state.get("request_type", "software")),
            user_message=state.get("user_message", ""),
            catalog_matched=bool(extraction.get("catalog_item_id")),
            catalog_enabled=bool(extraction.get("catalog_enabled")),
            catalog_risk=catalog_risk,
            catalog_approval_required=bool(extraction.get("catalog_approval_required")),
            resource=state.get("resource", ""),
        )
    )
    return {
        **state,
        "policy_decision": policy.decision.value,
        "risk_level": policy.risk_level.value,
        "approval_required": policy.approval_required,
        "reason": policy.reason,
        "route": policy.decision.value,
    }


def route_policy(state: ITGraphState) -> str:
    return state.get("route") or ITPolicyDecision.DENY.value


def planner_node(state: ITGraphState) -> ITGraphState:
    extraction = state.get("extraction") or {}
    plan = build_plan(
        runbook_id=extraction.get("catalog_runbook_id"),
        request_type=ITRequestType(state.get("request_type", "software")),
        resource=state.get("resource", ""),
        catalog_matched=bool(extraction.get("catalog_item_id")),
    )
    return {**state, "plan": plan}


def explain_denial_node(state: ITGraphState) -> ITGraphState:
    return state


def escalate_node(state: ITGraphState) -> ITGraphState:
    return state


def wait_for_approval_node(state: ITGraphState) -> ITGraphState:
    return state


_it_graph = None


def build_it_request_graph():
    global _it_graph
    if _it_graph is not None:
        return _it_graph

    graph = StateGraph(ITGraphState)
    graph.add_node("extract_entities", extract_entities_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("planner", planner_node)
    graph.add_node("explain_denial", explain_denial_node)
    graph.add_node("create_escalation", escalate_node)
    graph.add_node("wait_for_approval", wait_for_approval_node)

    graph.add_edge(START, "extract_entities")
    graph.add_edge("extract_entities", "policy_check")
    graph.add_conditional_edges(
        "policy_check",
        route_policy,
        {
            "allow": "planner",
            "deny": "explain_denial",
            "escalate": "create_escalation",
            "approval_required": "wait_for_approval",
        },
    )
    graph.add_edge("planner", END)
    graph.add_edge("explain_denial", END)
    graph.add_edge("create_escalation", END)
    graph.add_edge("wait_for_approval", END)

    _it_graph = graph.compile()
    return _it_graph


def reset_it_request_graph() -> None:
    global _it_graph
    _it_graph = None
