"""TOTP multi-factor authentication workflows.

Security properties (see docs/SECURITY.md):
- MFA is only marked enabled after the first code from the new secret verifies.
- Secrets are Fernet-encrypted at rest; recovery codes are stored as HMAC hashes.
- Accepted TOTP steps are remembered, so a code cannot be replayed.
- Repeated wrong codes lock the MFA step for MFA_LOCKOUT_MINUTES.
- No secret, OTP or recovery code is ever written to logs or audit payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.mfa import (
    MFASecretError,
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    match_totp_step,
    provisioning_uri,
    qr_svg_data_uri,
)
from app.core.security import verify_password
from app.models.enums import SecurityAuditEventType
from app.models.security import MFARecoveryCode, UserMFA
from app.models.user import User
from app.services.audit_service import record_audit_event

ENROLLMENT_TTL = timedelta(minutes=15)


class MFAError(Exception):
    """User-safe MFA failure (message is shown to the client)."""


class MFAInvalidCodeError(MFAError):
    pass


class MFALockedError(MFAError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many incorrect codes. Try again later.")
        self.retry_after_seconds = max(retry_after_seconds, 1)


class MFAStateError(MFAError):
    pass


class MFAReauthError(MFAError):
    pass


@dataclass
class EnrollmentStart:
    secret: str
    otpauth_uri: str
    qr_svg_data_uri: str


def _now() -> datetime:
    return datetime.now(UTC)


async def get_record(db: AsyncSession, user_id: UUID) -> UserMFA | None:
    return await db.get(UserMFA, user_id)


async def remaining_recovery_codes(db: AsyncSession, user_id: UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(MFARecoveryCode)
        .where(MFARecoveryCode.user_id == user_id, MFARecoveryCode.used_at.is_(None))
    )
    return int(count or 0)


def _ensure_not_locked(record: UserMFA) -> None:
    if record.locked_until and record.locked_until > _now():
        raise MFALockedError(int((record.locked_until - _now()).total_seconds()))


async def _register_failure(
    db: AsyncSession, record: UserMFA, settings: Settings, event: str, reason: str
) -> None:
    record.failed_attempts = (record.failed_attempts or 0) + 1
    locked = False
    if record.failed_attempts >= settings.MFA_MAX_FAILED_ATTEMPTS:
        record.locked_until = _now() + timedelta(minutes=settings.MFA_LOCKOUT_MINUTES)
        record.failed_attempts = 0
        locked = True
    await record_audit_event(db, event, user_id=record.user_id, payload={"reason": reason})
    if locked:
        await record_audit_event(
            db,
            SecurityAuditEventType.MFA_LOCKED.value,
            user_id=record.user_id,
            payload={"minutes": settings.MFA_LOCKOUT_MINUTES},
        )
    # Commit so failure counters persist even though the request then fails.
    await db.commit()


def _require_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise MFAReauthError("Password is incorrect")


# ------------------------------------------------------------ enrollment


async def start_enrollment(
    db: AsyncSession, user: User, settings: Settings | None = None
) -> EnrollmentStart:
    """Create a pending secret. MFA stays disabled until confirm_enrollment."""
    settings = settings or get_settings()
    record = await get_record(db, user.id)
    if record is not None and record.enabled:
        raise MFAStateError("MFA is already enabled. Disable it first to enroll a new authenticator.")
    if record is None:
        record = UserMFA(user_id=user.id, enabled=False, failed_attempts=0)
        db.add(record)
    _ensure_not_locked(record)
    secret = generate_totp_secret()
    record.pending_secret_encrypted = encrypt_secret(secret, settings)
    record.pending_created_at = _now()
    await record_audit_event(
        db, SecurityAuditEventType.MFA_ENROLLMENT_STARTED.value, user_id=user.id
    )
    await db.commit()
    uri = provisioning_uri(secret, user.email, settings.MFA_ISSUER)
    return EnrollmentStart(secret=secret, otpauth_uri=uri, qr_svg_data_uri=qr_svg_data_uri(uri))


async def _issue_recovery_codes(db: AsyncSession, user_id: UUID, settings: Settings) -> list[str]:
    await db.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
    codes = generate_recovery_codes(settings.MFA_RECOVERY_CODE_COUNT)
    for code in codes:
        db.add(MFARecoveryCode(user_id=user_id, code_hash=hash_recovery_code(code, settings)))
    await db.flush()
    return codes


async def confirm_enrollment(
    db: AsyncSession, user: User, code: str, settings: Settings | None = None
) -> list[str]:
    """Verify the first code against the pending secret; enable MFA; return codes once."""
    settings = settings or get_settings()
    record = await get_record(db, user.id)
    if record is None or not record.pending_secret_encrypted:
        raise MFAStateError("No MFA enrollment in progress. Start enrollment again.")
    if record.enabled:
        raise MFAStateError("MFA is already enabled.")
    _ensure_not_locked(record)
    if record.pending_created_at and _now() - record.pending_created_at > ENROLLMENT_TTL:
        record.pending_secret_encrypted = None
        record.pending_created_at = None
        await db.commit()
        raise MFAStateError("Enrollment expired. Start enrollment again.")
    try:
        secret = decrypt_secret(record.pending_secret_encrypted, settings)
    except MFASecretError as exc:
        raise MFAStateError("Enrollment could not be completed. Start enrollment again.") from exc
    step = match_totp_step(secret, code)
    if step is None:
        await _register_failure(
            db, record, settings, SecurityAuditEventType.MFA_ENROLLMENT_FAILED.value, "invalid_code"
        )
        raise MFAInvalidCodeError("That code is not valid. Check the time on your device and try again.")
    record.secret_encrypted = record.pending_secret_encrypted
    record.pending_secret_encrypted = None
    record.pending_created_at = None
    record.enabled = True
    record.enabled_at = _now()
    record.last_used_step = step
    record.failed_attempts = 0
    record.locked_until = None
    codes = await _issue_recovery_codes(db, user.id, settings)
    await record_audit_event(
        db,
        SecurityAuditEventType.MFA_ENABLED.value,
        user_id=user.id,
        payload={"recovery_codes_issued": len(codes)},
    )
    return codes


# ------------------------------------------------------------ verification


async def verify_second_factor(
    db: AsyncSession,
    user: User,
    *,
    code: str | None = None,
    recovery_code: str | None = None,
    settings: Settings | None = None,
    purpose: str = "login",
) -> str:
    """Verify a TOTP code or a single-use recovery code. Returns the method used.

    Raises MFAInvalidCodeError / MFALockedError / MFAStateError. On success the
    caller must commit (the accepted step / used code is flushed, not committed).
    """
    settings = settings or get_settings()
    record = await get_record(db, user.id)
    if record is None or not record.enabled or not record.secret_encrypted:
        raise MFAStateError("MFA is not enabled for this account.")
    _ensure_not_locked(record)

    if recovery_code:
        hashed = hash_recovery_code(recovery_code, settings)
        row = await db.scalar(
            select(MFARecoveryCode).where(
                MFARecoveryCode.user_id == user.id,
                MFARecoveryCode.code_hash == hashed,
                MFARecoveryCode.used_at.is_(None),
            )
        )
        if row is None:
            await _register_failure(
                db, record, settings, SecurityAuditEventType.MFA_VERIFY_FAILED.value,
                f"{purpose}:invalid_recovery_code",
            )
            raise MFAInvalidCodeError("That recovery code is not valid or was already used.")
        # Single use: conditional update so two concurrent requests cannot both win.
        result = await db.execute(
            update(MFARecoveryCode)
            .where(MFARecoveryCode.id == row.id, MFARecoveryCode.used_at.is_(None))
            .values(used_at=_now())
        )
        if (result.rowcount or 0) != 1:
            raise MFAInvalidCodeError("That recovery code is not valid or was already used.")
        record.failed_attempts = 0
        remaining = await remaining_recovery_codes(db, user.id)
        await record_audit_event(
            db,
            SecurityAuditEventType.MFA_RECOVERY_CODE_USED.value,
            user_id=user.id,
            payload={"purpose": purpose, "remaining": remaining},
        )
        return "recovery_code"

    if not code:
        raise MFAInvalidCodeError("Enter the 6-digit code from your authenticator app.")
    try:
        secret = decrypt_secret(record.secret_encrypted, settings)
    except MFASecretError as exc:
        raise MFAStateError(
            "MFA secret could not be read on the server. Use a recovery code or contact an administrator."
        ) from exc
    step = match_totp_step(secret, code, last_used_step=record.last_used_step)
    if step is None:
        await _register_failure(
            db, record, settings, SecurityAuditEventType.MFA_VERIFY_FAILED.value,
            f"{purpose}:invalid_or_reused_code",
        )
        raise MFAInvalidCodeError("That code is not valid or was already used.")
    record.last_used_step = step
    record.failed_attempts = 0
    await record_audit_event(
        db,
        SecurityAuditEventType.MFA_VERIFIED.value,
        user_id=user.id,
        payload={"purpose": purpose, "method": "totp"},
    )
    return "totp"


# ------------------------------------------------------------ management


async def regenerate_recovery_codes(
    db: AsyncSession, user: User, *, password: str, code: str, settings: Settings | None = None
) -> list[str]:
    settings = settings or get_settings()
    _require_password(user, password)
    await verify_second_factor(db, user, code=code, settings=settings, purpose="regenerate_codes")
    codes = await _issue_recovery_codes(db, user.id, settings)
    await record_audit_event(
        db,
        SecurityAuditEventType.MFA_RECOVERY_CODES_REGENERATED.value,
        user_id=user.id,
        payload={"recovery_codes_issued": len(codes)},
    )
    return codes


async def disable_mfa(
    db: AsyncSession,
    user: User,
    *,
    password: str,
    code: str | None,
    recovery_code: str | None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if settings.mfa_enforcement_mode == "strict" and settings.role_requires_mfa(user.role.value):
        raise MFAStateError("MFA is mandatory for your role and cannot be disabled.")
    try:
        _require_password(user, password)
    except MFAReauthError:
        await record_audit_event(
            db, SecurityAuditEventType.MFA_DISABLE_FAILED.value, user_id=user.id,
            payload={"reason": "invalid_password"},
        )
        await db.commit()
        raise
    await verify_second_factor(
        db, user, code=code, recovery_code=recovery_code, settings=settings, purpose="disable"
    )
    await _clear_mfa(db, user.id)
    await record_audit_event(db, SecurityAuditEventType.MFA_DISABLED.value, user_id=user.id)


async def _clear_mfa(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
    await db.execute(delete(UserMFA).where(UserMFA.user_id == user_id))
    await db.flush()


async def admin_reset_mfa(
    db: AsyncSession, *, admin: User, admin_password: str, target: User
) -> None:
    """Recovery path for a user who lost both authenticator and recovery codes."""
    if target.id == admin.id:
        raise MFAStateError("Use your own recovery codes to reset your MFA.")
    if not verify_password(admin_password, admin.password_hash):
        raise MFAReauthError("Password is incorrect")
    await _clear_mfa(db, target.id)
    await record_audit_event(
        db,
        SecurityAuditEventType.MFA_ADMIN_RESET.value,
        user_id=admin.id,
        payload={"target_user_id": str(target.id), "target_email": target.email},
    )
