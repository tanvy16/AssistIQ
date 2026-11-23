import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import Settings, get_settings
from app.models.enums import UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


BCRYPT_MAX_PASSWORD_BYTES = 72

# Hash of a random value, used so that a login for an unknown email still pays
# the full bcrypt cost (no timing signal for which emails exist).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        # bcrypt >= 5 raises on > 72 bytes; such passwords can never match.
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False


def burn_password_check(password: str) -> None:
    """Spend the same bcrypt work as a real check, for unknown users."""
    verify_password(password[:BCRYPT_MAX_PASSWORD_BYTES], _DUMMY_PASSWORD_HASH)


def create_access_token(
    user_id: UUID,
    role: UserRole,
    settings: Settings | None = None,
    *,
    mfa: bool = False,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "access",
        # True only when this session passed a TOTP / recovery-code challenge.
        "mfa": bool(mfa),
        "jti": secrets.token_hex(8),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


# Single-purpose, short-lived tokens used between the password step and the
# MFA step. get_current_user only accepts type == "access", so these can never
# be used to call normal application endpoints.
MFA_CHALLENGE_TOKEN = "mfa_challenge"
MFA_ENROLL_TOKEN = "mfa_enroll"


def create_purpose_token(
    user_id: UUID,
    purpose: str,
    minutes: int,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": purpose,
        "jti": secrets.token_hex(8),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_purpose_token(token: str, purpose: str, settings: Settings | None = None) -> UUID:
    settings = settings or get_settings()
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != purpose:
        raise jwt.InvalidTokenError("Invalid token type")
    return UUID(payload["sub"])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
