"""TOTP (RFC 6238), secret encryption and recovery-code primitives.

Nothing in this module logs or returns secrets on its own; callers decide what
leaves the server (only the enrollment-start response ever shows a secret).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
from functools import lru_cache
from urllib.parse import quote, urlencode

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
# Accept the previous and next 30 s step to tolerate phone/server clock drift.
TOTP_DRIFT_STEPS = 1
SECRET_BYTES = 20  # 160-bit secret, as recommended by RFC 4226.
RECOVERY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
RECOVERY_CODE_LENGTH = 10  # ~50 bits of entropy per code


class MFASecretError(Exception):
    """A stored secret could not be decrypted (wrong or rotated key)."""


# --------------------------------------------------------------------------- TOTP


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii").rstrip("=")


def _decode_secret(secret_b32: str) -> bytes:
    padded = secret_b32.upper() + "=" * (-len(secret_b32) % 8)
    return base64.b32decode(padded, casefold=True)


def hotp(key: bytes, counter: int, digits: int = TOTP_DIGITS, digest: str = "sha1") -> str:
    mac = hmac.new(key, struct.pack(">Q", counter), getattr(hashlib, digest)).digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def totp_at(secret_b32: str, for_time: float, digits: int = TOTP_DIGITS) -> str:
    return hotp(_decode_secret(secret_b32), int(for_time) // TOTP_PERIOD_SECONDS, digits)


def normalize_otp(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit())


def match_totp_step(
    secret_b32: str,
    code: str,
    *,
    now: float | None = None,
    last_used_step: int | None = None,
) -> int | None:
    """Return the matched time-step, or None.

    A code is rejected when it matches a step at or before ``last_used_step``
    (replay of an already-accepted code). Comparison is constant-time.
    """
    candidate = normalize_otp(code)
    if len(candidate) != TOTP_DIGITS:
        return None
    key = _decode_secret(secret_b32)
    current = int(now if now is not None else time.time()) // TOTP_PERIOD_SECONDS
    matched: int | None = None
    for step in range(current - TOTP_DRIFT_STEPS, current + TOTP_DRIFT_STEPS + 1):
        if hmac.compare_digest(hotp(key, step), candidate):
            matched = step
    if matched is None:
        return None
    if last_used_step is not None and matched <= last_used_step:
        return None
    return matched


def provisioning_uri(secret_b32: str, account_name: str, issuer: str) -> str:
    label = quote(f"{issuer}:{account_name}", safe="")
    params = urlencode(
        {
            "secret": secret_b32,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": TOTP_DIGITS,
            "period": TOTP_PERIOD_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{params}"


def qr_svg_data_uri(payload: str) -> str:
    import segno

    qr = segno.make(payload, error="m")
    # Dark modules on a white quiet zone: scanners need the contrast regardless
    # of the app theme.
    return qr.svg_data_uri(scale=5, border=3, dark="#0b0f0c", light="#ffffff")


# ----------------------------------------------------------------- encryption


def _derive_key(material: str, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(
        material.encode("utf-8")
    )


@lru_cache(maxsize=4)
def _fernet_for(key_setting: str | None, jwt_secret: str, app_env: str) -> Fernet:
    if key_setting:
        return Fernet(key_setting.encode("ascii"))
    if app_env == "production":  # also enforced by Settings validation
        raise RuntimeError("MFA_ENCRYPTION_KEY is required in production")
    logger.warning(
        "MFA_ENCRYPTION_KEY is not set; deriving the TOTP encryption key from "
        "JWT_SECRET_KEY (development/test only). Set a dedicated key for production."
    )
    derived = _derive_key(jwt_secret, b"assistiq-mfa-totp-secret-v1")
    return Fernet(base64.urlsafe_b64encode(derived))


def _fernet(settings: Settings | None = None) -> Fernet:
    settings = settings or get_settings()
    return _fernet_for(settings.MFA_ENCRYPTION_KEY, settings.JWT_SECRET_KEY, settings.APP_ENV)


def encrypt_secret(secret_b32: str, settings: Settings | None = None) -> str:
    return _fernet(settings).encrypt(secret_b32.encode("ascii")).decode("ascii")


def decrypt_secret(token: str, settings: Settings | None = None) -> str:
    try:
        return _fernet(settings).decrypt(token.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError) as exc:
        raise MFASecretError("Stored MFA secret could not be decrypted") from exc


# ------------------------------------------------------------- recovery codes


def generate_recovery_codes(count: int) -> list[str]:
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def hash_recovery_code(code: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    key = _derive_key(
        settings.MFA_ENCRYPTION_KEY or settings.JWT_SECRET_KEY, b"assistiq-mfa-recovery-code-v1"
    )
    return hmac.new(key, normalize_recovery_code(code).encode("ascii"), hashlib.sha256).hexdigest()


def reset_mfa_crypto_cache() -> None:
    _fernet_for.cache_clear()
