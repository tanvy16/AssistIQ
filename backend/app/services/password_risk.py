"""Deterministic password-reset risk assessment. The LLM never assigns risk."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.enums import UserRole
from app.models.password_reset import PasswordRiskLevel, PasswordVerificationStatus

SUSPICIOUS_KEYWORDS = (
    "someone else's",
    "another user",
    "other employee",
    "admin password",
    "domain admin",
    "service account",
    "break glass",
)


@dataclass(frozen=True)
class RiskInput:
    requester_id: UUID
    target_user_id: UUID
    requester_role: UserRole
    target_role: UserRole
    verification_status: PasswordVerificationStatus
    failed_verification_count: int
    user_message: str | None = None


@dataclass(frozen=True)
class RiskResult:
    risk_level: PasswordRiskLevel
    reason: str


def assess_password_reset_risk(payload: RiskInput) -> RiskResult:
    text = (payload.user_message or "").lower()
    if any(keyword in text for keyword in SUSPICIOUS_KEYWORDS):
        return RiskResult(PasswordRiskLevel.HIGH, "Request contains suspicious privileged or third-party language.")

    if payload.verification_status == PasswordVerificationStatus.FAILED:
        if payload.failed_verification_count >= 3:
            return RiskResult(PasswordRiskLevel.HIGH, "Repeated failed identity verification.")
        return RiskResult(PasswordRiskLevel.HIGH, "Identity verification failed.")

    if payload.verification_status == PasswordVerificationStatus.REQUIRES_ESCALATION:
        return RiskResult(PasswordRiskLevel.HIGH, "Identity verification requires human review.")

    if payload.requester_id != payload.target_user_id:
        return RiskResult(PasswordRiskLevel.HIGH, "Request targets a different user than the authenticated requester.")

    if payload.target_role == UserRole.ADMIN:
        return RiskResult(PasswordRiskLevel.CRITICAL, "Target account is a privileged administrator.")

    if payload.target_role == UserRole.AGENT:
        return RiskResult(PasswordRiskLevel.HIGH, "Target account is a privileged support agent.")

    if payload.requester_role != UserRole.EMPLOYEE:
        return RiskResult(PasswordRiskLevel.MEDIUM, "Privileged requester resetting their own account.")

    return RiskResult(PasswordRiskLevel.LOW, "Authenticated employee resetting their own standard account.")
