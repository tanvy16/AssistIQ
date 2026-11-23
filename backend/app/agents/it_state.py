"""IT request LangGraph state."""

from __future__ import annotations

from typing import Any, TypedDict


class ITGraphState(TypedDict, total=False):
    user_message: str
    request_type: str
    resource: str
    extraction: dict[str, Any]
    policy_decision: str
    risk_level: str
    approval_required: bool
    reason: str
    plan: dict[str, Any]
    execution_result: dict[str, Any]
    validation: dict[str, Any]
    rollback_result: dict[str, Any]
    route: str
    error: str | None
