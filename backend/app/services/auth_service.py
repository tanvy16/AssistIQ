import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    burn_password_check,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.enums import AuthAuditEventType, UserRole
from app.models.refresh_token import RefreshToken
from app.models.security import LoginThrottle, UserMFA
from app.models.user import User
from app.services.audit_service import record_audit_event


class AuthError(Exception):
    pass


class InvalidCredentialsError(AuthError):
    pass


class AccountLockedError(AuthError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Account temporarily locked")
        self.retry_after_seconds = max(retry_after_seconds, 1)


class InvalidRefreshTokenError(AuthError):
    pass


class PasswordPolicyError(AuthError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


# --------------------------------------------------------------- lockout


async def _get_throttle(db: AsyncSession, email: str) -> LoginThrottle | None:
    return await db.get(LoginThrottle, email.lower())


async def ensure_not_locked(db: AsyncSession, email: str) -> None:
    throttle = await _get_throttle(db, email)
    if throttle and throttle.locked_until and throttle.locked_until > _now():
        raise AccountLockedError(int((throttle.locked_until - _now()).total_seconds()))


async def register_login_failure(
    db: AsyncSession, email: str, settings: Settings | None = None
) -> bool:
    """Count a failed login. Returns True when this failure triggered a lockout.

    Keyed on the normalised email whether or not the account exists, so the
    response behaviour never reveals which emails are registered.
    """
    settings = settings or get_settings()
    key = email.lower()
    now = _now()
    throttle = await _get_throttle(db, key)
    if throttle is None:
        throttle = LoginThrottle(email=key, failed_count=0, window_started_at=now)
        db.add(throttle)
    window = timedelta(minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES)
    if throttle.window_started_at is None or now - throttle.window_started_at > window:
        throttle.failed_count = 0
        throttle.window_started_at = now
    throttle.failed_count += 1
    locked_now = False
    if throttle.failed_count >= settings.LOGIN_LOCKOUT_THRESHOLD:
        throttle.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        throttle.failed_count = 0
        throttle.window_started_at = now
        locked_now = True
    await db.flush()
    return locked_now


async def clear_login_failures(db: AsyncSession, email: str) -> None:
    throttle = await _get_throttle(db, email)
    if throttle is not None:
        throttle.failed_count = 0
        throttle.window_started_at = None
        throttle.locked_until = None
        await db.flush()


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not user.is_active:
        burn_password_check(password)
        raise InvalidCredentialsError()
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


# --------------------------------------------------------------- MFA state


async def get_mfa_enabled(db: AsyncSession, user_id: UUID) -> bool:
    enabled = await db.scalar(select(UserMFA.enabled).where(UserMFA.user_id == user_id))
    return bool(enabled)


def mfa_enrollment_required(user: User, mfa_enabled: bool, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return (not mfa_enabled) and settings.role_requires_mfa(user.role.value)


# --------------------------------------------------------------- tokens


async def _store_refresh_token(
    db: AsyncSession,
    user_id: UUID,
    raw_token: str,
    settings: Settings,
    user_agent: str | None = None,
    *,
    family_id: UUID | None = None,
    mfa_verified: bool = False,
) -> RefreshToken:
    record = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(user_agent or "")[:512] or None,
        family_id=family_id or uuid.uuid4(),
        mfa_verified=mfa_verified,
    )
    db.add(record)
    await db.flush()
    return record


async def issue_token_pair(
    db: AsyncSession,
    user: User,
    settings: Settings | None = None,
    user_agent: str | None = None,
    *,
    mfa_verified: bool = False,
) -> tuple[str, str]:
    settings = settings or get_settings()
    access_token = create_access_token(user.id, user.role, settings, mfa=mfa_verified)
    raw_refresh = generate_refresh_token()
    await _store_refresh_token(
        db, user.id, raw_refresh, settings, user_agent, mfa_verified=mfa_verified
    )
    await db.commit()
    return access_token, raw_refresh


async def _revoke_family(db: AsyncSession, family_id: UUID | None, user_id: UUID) -> int:
    if family_id is None:
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    else:
        stmt = update(RefreshToken).where(
            RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None)
        )
    result = await db.execute(stmt.values(revoked_at=_now()))
    return int(result.rowcount or 0)


async def rotate_refresh_token(
    db: AsyncSession,
    raw_refresh: str,
    settings: Settings | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, User]:
    settings = settings or get_settings()
    token_hash = hash_refresh_token(raw_refresh)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = _now()

    if record is None:
        raise InvalidRefreshTokenError()

    if record.revoked_at is not None:
        # A rotated token presented again outside the short grace window means
        # two parties hold the same token: revoke the whole family.
        rotated = record.replaced_by_id is not None
        grace = timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS)
        if rotated and now - record.revoked_at > grace:
            revoked = await _revoke_family(db, record.family_id, record.user_id)
            await record_audit_event(
                db,
                AuthAuditEventType.REFRESH_REUSE_DETECTED.value,
                user_id=record.user_id,
                payload={"revoked_sessions": revoked},
            )
            await db.commit()
        raise InvalidRefreshTokenError()

    if record.expires_at <= now:
        raise InvalidRefreshTokenError()

    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    mfa_enabled = await get_mfa_enabled(db, user.id)
    if mfa_enabled and not record.mfa_verified:
        # Session predates MFA enrollment (or never passed MFA): it cannot be
        # renewed into an MFA-enabled account's access token.
        record.revoked_at = now
        await record_audit_event(
            db, AuthAuditEventType.REFRESH_REJECTED_MFA.value, user_id=user.id
        )
        await db.commit()
        raise InvalidRefreshTokenError()

    if (
        settings.mfa_enforcement_mode == "strict"
        and mfa_enrollment_required(user, mfa_enabled, settings)
    ):
        raise InvalidRefreshTokenError()

    new_raw_refresh = generate_refresh_token()
    new_record = await _store_refresh_token(
        db,
        user.id,
        new_raw_refresh,
        settings,
        user_agent,
        family_id=record.family_id,
        mfa_verified=record.mfa_verified,
    )
    record.revoked_at = now
    record.replaced_by_id = new_record.id
    access_token = create_access_token(user.id, user.role, settings, mfa=record.mfa_verified)
    await record_audit_event(
        db,
        AuthAuditEventType.REFRESH.value,
        user_id=user.id,
        payload={"email": user.email},
    )
    await db.commit()
    return access_token, new_raw_refresh, user


async def revoke_refresh_token(db: AsyncSession, raw_refresh: str) -> None:
    token_hash = hash_refresh_token(raw_refresh)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record is not None and record.revoked_at is None:
        record.revoked_at = _now()
        await record_audit_event(
            db,
            AuthAuditEventType.LOGOUT.value,
            user_id=record.user_id,
        )
        await db.commit()


async def find_refresh_record(db: AsyncSession, raw_refresh: str | None) -> RefreshToken | None:
    if not raw_refresh:
        return None
    return await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_refresh))
    )


async def revoke_other_sessions(
    db: AsyncSession, user_id: UUID, keep_token_id: UUID | None
) -> int:
    stmt = update(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    if keep_token_id is not None:
        stmt = stmt.where(RefreshToken.id != keep_token_id)
    result = await db.execute(stmt.values(revoked_at=_now()))
    return int(result.rowcount or 0)


async def list_active_sessions(db: AsyncSession, user_id: UUID) -> list[RefreshToken]:
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > _now(),
        )
        .order_by(RefreshToken.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


# --------------------------------------------------------------- passwords


PASSWORD_MIN_LENGTH = 12


def validate_new_password(password: str, *, email: str, current_password: str | None = None) -> None:
    """Reject weak passwords. Raises PasswordPolicyError with a user-safe message."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise PasswordPolicyError("Password must be at most 72 bytes")
    classes = sum(
        [
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        ]
    )
    if classes < 3:
        raise PasswordPolicyError(
            "Password must mix at least three of: lowercase, uppercase, digits, symbols"
        )
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 4 and local_part in password.lower():
        raise PasswordPolicyError("Password must not contain your email name")
    if current_password is not None and password == current_password:
        raise PasswordPolicyError("New password must differ from the current password")


async def change_password(
    db: AsyncSession,
    user: User,
    new_password: str,
) -> None:
    user.password_hash = hash_password(new_password)
    await db.flush()


def build_user_public(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name,
        "is_active": user.is_active,
    }


async def ensure_seed_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: UserRole,
    display_name: str,
) -> User:
    existing = await get_user_by_email(db, email)
    if existing is not None:
        return existing

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
