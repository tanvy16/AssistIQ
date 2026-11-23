"""Session-authoritative identity verification. LLM claims are ignored."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.enums import UserRole
from app.models.password_reset import PasswordVerificationStatus
from app.models.user import User

SUSPICIOUS_CLAIMS = (
    "i am admin",
    "i am the admin",
    "username is admin",
    "i am root",
    "trust me",
)


@dataclass(frozen=True)
class VerificationInput:
    actor: User
    target_user_id: UUID
    submitted_email: str | None
    user_message: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    status: PasswordVerificationStatus
    reason: str


def verify_identity(payload: VerificationInput) -> VerificationResult:
    submitted = (payload.submitted_email or "").strip().lower()
    if not submitted:
        return VerificationResult(
            PasswordVerificationStatus.FAILED,
            "Registered email confirmation is required.",
        )

    message = (payload.user_message or "").lower()
    if any(claim in message for claim in SUSPICIOUS_CLAIMS):
        return VerificationResult(
            PasswordVerificationStatus.REQUIRES_ESCALATION,
            "Self-asserted privileged identity is not accepted.",
        )

    if submitted != payload.actor.email.lower():
        return VerificationResult(
            PasswordVerificationStatus.FAILED,
            "Submitted email does not match the authenticated session identity.",
        )

    if payload.actor.id != payload.target_user_id:
        if payload.actor.role == UserRole.EMPLOYEE:
            return VerificationResult(
                PasswordVerificationStatus.FAILED,
                "Employees can only verify a password reset for their own account.",
            )
        return VerificationResult(
            PasswordVerificationStatus.REQUIRES_ESCALATION,
            "Resetting another user's password requires human review.",
        )

    return VerificationResult(
        PasswordVerificationStatus.VERIFIED,
        "Authenticated session identity matched the registered email.",
    )
