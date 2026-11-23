"""Deterministic password-reset policy. The LLM never decides allow/deny."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.enums import UserRole
from app.models.password_reset import (
    PasswordPolicyDecision,
    PasswordRiskLevel,
    PasswordVerificationStatus,
)


@dataclass(frozen=True)
class PasswordPolicyInput:
    requester_id: UUID
    target_user_id: UUID
    requester_role: UserRole
    verification_status: PasswordVerificationStatus
    risk_level: PasswordRiskLevel


@dataclass(frozen=True)
class PasswordPolicyResult:
    decision: PasswordPolicyDecision
    reason: str


def evaluate_password_reset_policy(payload: PasswordPolicyInput) -> PasswordPolicyResult:
    if payload.requester_role == UserRole.EMPLOYEE and payload.requester_id != payload.target_user_id:
        return PasswordPolicyResult(
            PasswordPolicyDecision.DENY,
            "Employees cannot reset another user's password.",
        )

    if payload.verification_status == PasswordVerificationStatus.FAILED:
        if payload.risk_level in {PasswordRiskLevel.HIGH, PasswordRiskLevel.CRITICAL}:
            return PasswordPolicyResult(
                PasswordPolicyDecision.REQUIRES_ESCALATION,
                "Failed verification on a high-risk request requires human review.",
            )
        return PasswordPolicyResult(
            PasswordPolicyDecision.DENY,
            "Identity verification failed.",
        )

    if payload.verification_status != PasswordVerificationStatus.VERIFIED:
        return PasswordPolicyResult(
            PasswordPolicyDecision.REQUIRES_ESCALATION,
            "Identity was not fully verified.",
        )

    if payload.risk_level in {PasswordRiskLevel.HIGH, PasswordRiskLevel.CRITICAL}:
        return PasswordPolicyResult(
            PasswordPolicyDecision.REQUIRES_ESCALATION,
            "High-risk or privileged password resets cannot execute automatically.",
        )

    if payload.risk_level == PasswordRiskLevel.MEDIUM:
        return PasswordPolicyResult(
            PasswordPolicyDecision.REQUIRES_CONFIRMATION,
            "Additional confirmation is required before simulated reset.",
        )

    return PasswordPolicyResult(
        PasswordPolicyDecision.REQUIRES_CONFIRMATION,
        "Verified low-risk request may proceed after explicit confirmation.",
    )
