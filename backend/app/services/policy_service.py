"""Deterministic IT request policy engine. The LLM never decides allow/deny."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.it_request import ITPolicyDecision, ITRequestType, ITRiskLevel

CRITICAL_KEYWORDS = (
    "domain admin",
    "domain administrator",
    "unrestricted production",
    "security infrastructure",
    "root access",
    "break glass",
)

PRIVILEGED_KEYWORDS = (
    "admin privileges",
    "administrator",
    "elevated access",
    "privileged",
    "production access",
    "sudo",
    "local admin",
)


@dataclass(frozen=True)
class PolicyInput:
    request_type: ITRequestType
    user_message: str
    catalog_matched: bool
    catalog_enabled: bool
    catalog_risk: ITRiskLevel | None
    catalog_approval_required: bool
    resource: str


@dataclass(frozen=True)
class PolicyResult:
    decision: ITPolicyDecision
    risk_level: ITRiskLevel
    approval_required: bool
    reason: str


def evaluate_policy(payload: PolicyInput) -> PolicyResult:
    text = payload.user_message.lower()

    if any(keyword in text for keyword in CRITICAL_KEYWORDS):
        return PolicyResult(
            ITPolicyDecision.ESCALATE,
            ITRiskLevel.CRITICAL,
            True,
            "Critical privilege or infrastructure access requires human escalation.",
        )

    if payload.request_type == ITRequestType.PERMISSION or any(
        keyword in text for keyword in PRIVILEGED_KEYWORDS
    ):
        return PolicyResult(
            ITPolicyDecision.ESCALATE,
            ITRiskLevel.HIGH,
            True,
            "Privileged access cannot be executed automatically and requires human review.",
        )

    if not payload.catalog_matched:
        return PolicyResult(
            ITPolicyDecision.DENY,
            ITRiskLevel.MEDIUM,
            False,
            "Requested resource is not in the approved catalog.",
        )

    if not payload.catalog_enabled:
        return PolicyResult(
            ITPolicyDecision.DENY,
            ITRiskLevel.MEDIUM,
            False,
            "Requested catalog item is disabled.",
        )

    risk = payload.catalog_risk or ITRiskLevel.MEDIUM

    if risk == ITRiskLevel.CRITICAL:
        return PolicyResult(
            ITPolicyDecision.ESCALATE,
            risk,
            True,
            "Catalog item is classified as critical and requires human escalation.",
        )

    if risk == ITRiskLevel.HIGH or payload.catalog_approval_required:
        return PolicyResult(
            ITPolicyDecision.APPROVAL_REQUIRED,
            risk,
            True,
            "Policy requires approval before this request can proceed.",
        )

    if risk == ITRiskLevel.MEDIUM:
        return PolicyResult(
            ITPolicyDecision.APPROVAL_REQUIRED,
            risk,
            True,
            "Medium-risk catalog items require approval.",
        )

    return PolicyResult(
        ITPolicyDecision.ALLOW,
        ITRiskLevel.LOW,
        False,
        "Approved low-risk catalog item may proceed to simulated execution.",
    )
