"""Research-only reimplementation of Baseline A algorithms (mirrors production logic)."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

_WHITESPACE_RE = re.compile(r"\s+")

INTENT_ROUTE_MAP = {
    "knowledge_query": "retrieve_context",
    "ticket_query": "retrieve_ticket_context",
    "ticket_creation_request": "retrieve_ticket_context",
    "general_query": "retrieve_context",
    "password_reset_request": "start_password_reset",
    "software_access_request": "start_it_request",
    "human_escalation": "escalate",
    "unsupported": "handle_unsupported",
}

_KEYWORD_INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("human_escalation", ("human", "agent", "representative", "escalate", "speak to")),
    (
        "password_reset_request",
        (
            "password reset",
            "reset password",
            "reset my password",
            "forgot password",
            "change password",
        ),
    ),
    (
        "software_access_request",
        (
            "install software",
            "software access",
            "access request",
            "need access to",
            "give me access",
            "need vscode",
            "need vs code",
            "visual studio code",
            "install python",
            "need python",
            "install git",
            "need git",
            "7-zip",
            "7zip",
            "microsoft visio",
            "microsoft office",
            "need office",
            "finance shared drive",
            "jira",
            "confluence",
            "monitoring dashboard",
            "admin privileges",
            "elevated access",
            "installed",
        ),
    ),
    (
        "ticket_creation_request",
        ("create ticket", "open ticket", "new ticket", "submit ticket"),
    ),
    ("ticket_query", ("my ticket", "ticket status", "ticket #", "ticket number")),
    (
        "knowledge_query",
        ("how do i", "how to", "guide", "policy", "procedure", "vpn", "wifi"),
    ),
]

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


def normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def keyword_intent(text: str) -> str:
    lowered = text.lower()
    for intent, keywords in _KEYWORD_INTENTS:
        if any(keyword in lowered for keyword in keywords):
            return intent
    if re.search(r"\?", text):
        return "general_query"
    return "knowledge_query"


def route_for_intent(intent: str) -> str:
    return INTENT_ROUTE_MAP.get(intent, "handle_unsupported")


def hash_embed(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    normalized = normalize_text(text)
    if not normalized:
        return vector
    for token in normalized.split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for byte_idx, byte_val in enumerate(digest):
            index = (byte_val + byte_idx) % dim
            vector[index] += 1.0 + (byte_val / 255.0)
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def confidence_label(top_score: float | None, citation_count: int) -> str:
    if citation_count < 1 or top_score is None:
        return "NO_EVIDENCE"
    if top_score >= 0.65:
        return "HIGH_CONFIDENCE"
    if top_score >= 0.35:
        return "LOW_CONFIDENCE"
    return "NO_EVIDENCE"


def evaluate_it_policy(
    *,
    request_type: str,
    user_message: str,
    catalog_matched: bool,
    catalog_enabled: bool,
    catalog_risk: str | None,
    catalog_approval_required: bool,
) -> str:
    text = user_message.lower()
    if any(k in text for k in CRITICAL_KEYWORDS):
        return "ESCALATE"
    if request_type == "PERMISSION" or any(k in text for k in PRIVILEGED_KEYWORDS):
        return "ESCALATE"
    if not catalog_matched:
        return "DENY"
    if not catalog_enabled:
        return "DENY"
    risk = catalog_risk or "MEDIUM"
    if risk == "CRITICAL":
        return "ESCALATE"
    if risk == "HIGH" or catalog_approval_required:
        return "APPROVAL_REQUIRED"
    if risk == "MEDIUM":
        return "APPROVAL_REQUIRED"
    return "ALLOW"


def password_policy(
    *,
    employee_other_user: bool,
    verification: str,
    risk: str,
) -> str:
    if employee_other_user:
        return "DENY"
    if verification == "FAILED" and risk in {"HIGH", "CRITICAL"}:
        return "ESCALATE"
    if verification == "FAILED":
        return "DENY"
    if verification != "VERIFIED":
        return "ESCALATE"
    if risk in {"HIGH", "CRITICAL"}:
        return "ESCALATE"
    return "REQUIRE_CONFIRMATION"
