"""Password reset LangGraph state."""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID

from app.models.user import User


class PasswordResetGraphState(TypedDict, total=False):
    requester_id: UUID
    target_user_id: UUID
    submitted_email: str | None
    user_message: str | None
    target_role: str
    verification_status: str
    failed_verification_count: int
    risk_level: str
    policy_decision: str
    reason: str
    route: str
    _actor: User
    extra: dict[str, Any]
