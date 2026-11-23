"""Password reset LangGraph — policy orchestration only; persistence is in PasswordResetService."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.password_reset_state import PasswordResetGraphState
from app.models.enums import UserRole
from app.models.password_reset import PasswordRiskLevel, PasswordVerificationStatus
from app.services.password_reset_policy import PasswordPolicyInput, evaluate_password_reset_policy
from app.services.password_risk import RiskInput, assess_password_reset_risk
from app.services.password_verification import VerificationInput, verify_identity
from app.models.user import User


def verify_identity_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    actor = state.get("_actor")
    if actor is None:
        return {**state, "route": "deny", "reason": "Authenticated identity is required."}
    result = verify_identity(
        VerificationInput(
            actor=actor,
            target_user_id=state["target_user_id"],
            submitted_email=state.get("submitted_email"),
            user_message=state.get("user_message"),
        )
    )
    return {**state, "verification_status": result.status.value, "reason": result.reason}


def risk_assessment_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    actor: User | None = state.get("_actor")
    target_role = UserRole(state.get("target_role") or UserRole.EMPLOYEE.value)
    risk = assess_password_reset_risk(
        RiskInput(
            requester_id=state["requester_id"],
            target_user_id=state["target_user_id"],
            requester_role=actor.role if actor else UserRole.EMPLOYEE,
            target_role=target_role,
            verification_status=PasswordVerificationStatus(state.get("verification_status", "pending")),
            failed_verification_count=int(state.get("failed_verification_count") or 0),
            user_message=state.get("user_message"),
        )
    )
    return {**state, "risk_level": risk.risk_level.value, "reason": risk.reason}


def policy_check_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    actor: User | None = state.get("_actor")
    policy = evaluate_password_reset_policy(
        PasswordPolicyInput(
            requester_id=state["requester_id"],
            target_user_id=state["target_user_id"],
            requester_role=actor.role if actor else UserRole.EMPLOYEE,
            verification_status=PasswordVerificationStatus(state.get("verification_status", "pending")),
            risk_level=PasswordRiskLevel(state.get("risk_level") or "high"),
        )
    )
    route = {
        "deny": "deny",
        "requires_escalation": "escalate",
        "requires_confirmation": "confirmation",
        "allow": "execute",
    }.get(policy.decision.value, "deny")
    return {**state, "policy_decision": policy.decision.value, "reason": policy.reason, "route": route}


def route_policy(state: PasswordResetGraphState) -> str:
    return state.get("route") or "deny"


def deny_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    return state


def escalate_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    return state


def confirmation_node(state: PasswordResetGraphState) -> PasswordResetGraphState:
    return state


_graph = None


def build_password_reset_graph():
    global _graph
    if _graph is not None:
        return _graph

    graph = StateGraph(PasswordResetGraphState)
    graph.add_node("verify_identity", verify_identity_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("deny", deny_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("wait_for_confirmation", confirmation_node)

    graph.add_edge(START, "verify_identity")
    graph.add_edge("verify_identity", "risk_assessment")
    graph.add_edge("risk_assessment", "policy_check")
    graph.add_conditional_edges(
        "policy_check",
        route_policy,
        {
            "deny": "deny",
            "escalate": "escalate",
            "confirmation": "wait_for_confirmation",
            "execute": "wait_for_confirmation",
        },
    )
    graph.add_edge("deny", END)
    graph.add_edge("escalate", END)
    graph.add_edge("wait_for_confirmation", END)

    _graph = graph.compile()
    return _graph


def reset_password_reset_graph() -> None:
    global _graph
    _graph = None
