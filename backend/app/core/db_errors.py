import re
from typing import Any


_CREDENTIAL_PATTERNS = (
    re.compile(r"postgresql(\+asyncpg)?://[^@\s]+@", re.IGNORECASE),
    re.compile(r"password[=:]\S+", re.IGNORECASE),
    re.compile(r"token[=:]\S+", re.IGNORECASE),
)


def sanitize_error_message(message: str) -> str:
    redacted = message
    for pattern in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def classify_database_error(exc: Exception) -> str:
    message = sanitize_error_message(str(exc)).lower()
    exc_type = type(exc).__name__

    if exc_type in {"gaierror", "ClientConnectorDNSError"} or "getaddrinfo failed" in message:
        return "dns_resolution_failed"
    if "password authentication failed" in message or "invalid authorization" in message:
        return "authentication_failed"
    if "certificate" in message or "ssl" in message or "tls" in message:
        return "ssl_error"
    if "timeout" in message or "timed out" in message:
        return "connection_timeout"
    if "connection refused" in message or "could not connect" in message:
        return "connection_refused"
    if "does not exist" in message and "database" in message:
        return "database_not_found"
    if "unexpected keyword argument" in message:
        return "invalid_connection_options"
    if "field required" in message or "database_url" in message:
        return "configuration_missing"
    return "connection_failed"


def build_db_diagnostic(exc: Exception) -> dict[str, Any]:
    return {
        "error_type": type(exc).__name__,
        "error_category": classify_database_error(exc),
        "error_message": sanitize_error_message(str(exc)),
    }
