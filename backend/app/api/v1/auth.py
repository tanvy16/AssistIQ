from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, get_user_for_mfa_enrollment
from app.core.rate_limit import rate_limit
from app.core.security import (
    MFA_CHALLENGE_TOKEN,
    MFA_ENROLL_TOKEN,
    create_purpose_token,
    decode_purpose_token,
    verify_password,
)
from app.models.enums import AuthAuditEventType, SecurityAuditEventType
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutResponse,
    MFADisableRequest,
    MFAEnrollStartResponse,
    MFAEnrollVerifyRequest,
    MFARecoveryCodesResponse,
    MFARegenerateRequest,
    MFAStatusResponse,
    MFAVerifyRequest,
    PasswordChangeRequest,
    PasswordReauthRequest,
    SessionInfo,
    SessionListResponse,
    SessionsRevokedResponse,
    TokenResponse,
    UserPublic,
)
from app.services import mfa_service
from app.services.audit_service import record_audit_event
from app.services.auth_service import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PasswordPolicyError,
    authenticate_user,
    change_password,
    clear_login_failures,
    ensure_not_locked,
    find_refresh_record,
    get_mfa_enabled,
    issue_token_pair,
    list_active_sessions,
    mfa_enrollment_required,
    register_login_failure,
    revoke_other_sessions,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_new_password,
)

router = APIRouter(prefix="/auth")

GENERIC_LOGIN_ERROR = "Invalid email or password"
LOCKED_ERROR = "Too many failed sign-in attempts. Try again later."


def _set_refresh_cookie(response: Response, raw_refresh: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
    )


def user_public(user: User, mfa_enabled: bool, settings: Settings | None = None) -> UserPublic:
    base = UserPublic.model_validate(user)
    return base.model_copy(
        update={
            "mfa_enabled": mfa_enabled,
            "mfa_enrollment_required": mfa_enrollment_required(user, mfa_enabled, settings),
        }
    )


def _mfa_http_error(exc: mfa_service.MFAError) -> HTTPException:
    if isinstance(exc, mfa_service.MFALockedError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
    if isinstance(exc, mfa_service.MFAStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, mfa_service.MFAReauthError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ------------------------------------------------------------------ login


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login"))])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = payload.email.lower()
    try:
        await ensure_not_locked(db, email)
    except AccountLockedError as exc:
        await record_audit_event(
            db, AuthAuditEventType.LOGIN_BLOCKED.value, payload={"email": email}
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=LOCKED_ERROR,
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    try:
        user = await authenticate_user(db, email, payload.password)
    except InvalidCredentialsError as exc:
        locked = await register_login_failure(db, email, settings)
        await record_audit_event(
            db, AuthAuditEventType.LOGIN_FAILED.value, payload={"email": email}
        )
        if locked:
            await record_audit_event(
                db,
                AuthAuditEventType.ACCOUNT_LOCKED.value,
                payload={"email": email, "minutes": settings.LOGIN_LOCKOUT_MINUTES},
            )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR
        ) from exc

    await clear_login_failures(db, email)
    mfa_enabled = await get_mfa_enabled(db, user.id)

    if mfa_enabled:
        # Password step passed; no access token or cookie until the second factor.
        await record_audit_event(
            db, SecurityAuditEventType.MFA_CHALLENGE_ISSUED.value, user_id=user.id
        )
        await db.commit()
        return TokenResponse(
            mfa_required=True,
            mfa_token=create_purpose_token(
                user.id, MFA_CHALLENGE_TOKEN, settings.MFA_CHALLENGE_TOKEN_MINUTES, settings
            ),
        )

    needs_enrollment = mfa_enrollment_required(user, mfa_enabled, settings)
    if needs_enrollment and settings.mfa_enforcement_mode == "strict":
        await record_audit_event(
            db,
            AuthAuditEventType.LOGIN.value,
            user_id=user.id,
            payload={"email": user.email, "result": "mfa_enrollment_required"},
        )
        await db.commit()
        return TokenResponse(
            mfa_enrollment_required=True,
            enrollment_token=create_purpose_token(user.id, MFA_ENROLL_TOKEN, 15, settings),
        )

    access_token, raw_refresh = await issue_token_pair(
        db, user, settings, user_agent=request.headers.get("user-agent")
    )
    await record_audit_event(
        db,
        AuthAuditEventType.LOGIN.value,
        user_id=user.id,
        payload={"email": user.email, "mfa": False},
    )
    await db.commit()
    _set_refresh_cookie(response, raw_refresh, settings)
    return TokenResponse(
        access_token=access_token,
        user=user_public(user, mfa_enabled, settings),
        mfa_enrollment_required=needs_enrollment,
    )


@router.post(
    "/mfa/verify", response_model=TokenResponse, dependencies=[Depends(rate_limit("mfa"))]
)
async def verify_mfa_login(
    payload: MFAVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        user_id = decode_purpose_token(payload.mfa_token, MFA_CHALLENGE_TOKEN, settings)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign-in step expired. Enter your password again.",
        ) from exc
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)
    try:
        method = await mfa_service.verify_second_factor(
            db, user, code=payload.code, recovery_code=payload.recovery_code, settings=settings
        )
    except mfa_service.MFAError as exc:
        raise _mfa_http_error(exc) from exc

    access_token, raw_refresh = await issue_token_pair(
        db, user, settings, user_agent=request.headers.get("user-agent"), mfa_verified=True
    )
    await record_audit_event(
        db,
        AuthAuditEventType.LOGIN.value,
        user_id=user.id,
        payload={"email": user.email, "mfa": True, "method": method},
    )
    await db.commit()
    _set_refresh_cookie(response, raw_refresh, settings)
    return TokenResponse(access_token=access_token, user=user_public(user, True, settings))


# ------------------------------------------------------------------ session


@router.post("/refresh", response_model=AccessTokenResponse, dependencies=[Depends(rate_limit("refresh"))])
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        access_token, new_raw_refresh, user = await rotate_refresh_token(
            db,
            raw_refresh,
            settings,
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidRefreshTokenError as exc:
        _clear_refresh_cookie(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    mfa_enabled = await get_mfa_enabled(db, user.id)
    _set_refresh_cookie(response, new_raw_refresh, settings)
    return AccessTokenResponse(
        access_token=access_token, user=user_public(user, mfa_enabled, settings)
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw_refresh:
        await revoke_refresh_token(db, raw_refresh)
    _clear_refresh_cookie(response, settings)
    return LogoutResponse()


@router.get("/me", response_model=UserPublic)
async def me(
    request: Request,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return user_public(current_user, bool(getattr(request.state, "mfa_enabled", False)), settings)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    current = await find_refresh_record(db, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    records = await list_active_sessions(db, current_user.id)
    return SessionListResponse(
        items=[
            SessionInfo(
                id=r.id,
                created_at=r.created_at,
                expires_at=r.expires_at,
                user_agent=r.user_agent,
                mfa_verified=r.mfa_verified,
                current=current is not None and current.id == r.id,
            )
            for r in records
        ]
    )


@router.post("/sessions/revoke-others", response_model=SessionsRevokedResponse)
async def revoke_other_session_tokens(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    current = await find_refresh_record(db, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    keep = current.id if current is not None and current.user_id == current_user.id else None
    revoked = await revoke_other_sessions(db, current_user.id, keep)
    await record_audit_event(
        db,
        AuthAuditEventType.SESSIONS_REVOKED.value,
        user_id=current_user.id,
        payload={"revoked": revoked, "reason": "user_request"},
    )
    await db.commit()
    return SessionsRevokedResponse(revoked=revoked)


@router.post(
    "/password/change",
    response_model=SessionsRevokedResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def change_own_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        await record_audit_event(
            db,
            AuthAuditEventType.PASSWORD_CHANGE_FAILED.value,
            user_id=current_user.id,
            payload={"reason": "invalid_current_password"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    try:
        validate_new_password(
            payload.new_password,
            email=current_user.email,
            current_password=payload.current_password,
        )
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if bool(getattr(request.state, "mfa_enabled", False)):
        if not payload.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter the code from your authenticator app",
            )
        try:
            await mfa_service.verify_second_factor(
                db, current_user, code=payload.code, settings=settings, purpose="password_change"
            )
        except mfa_service.MFAError as exc:
            raise _mfa_http_error(exc) from exc
    await change_password(db, current_user, payload.new_password)
    current = await find_refresh_record(db, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    keep = current.id if current is not None and current.user_id == current_user.id else None
    revoked = await revoke_other_sessions(db, current_user.id, keep)
    await record_audit_event(
        db,
        AuthAuditEventType.PASSWORD_CHANGED.value,
        user_id=current_user.id,
        payload={"other_sessions_revoked": revoked},
    )
    await db.commit()
    return SessionsRevokedResponse(revoked=revoked)


# ------------------------------------------------------------------ MFA management


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def mfa_status(
    current_user: User = Depends(get_user_for_mfa_enrollment),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    record = await mfa_service.get_record(db, current_user.id)
    enabled = bool(record and record.enabled)
    return MFAStatusResponse(
        enabled=enabled,
        enabled_at=record.enabled_at if record else None,
        pending_enrollment=bool(record and record.pending_secret_encrypted and not enabled),
        recovery_codes_remaining=(
            await mfa_service.remaining_recovery_codes(db, current_user.id) if enabled else 0
        ),
        required_for_role=settings.role_requires_mfa(current_user.role.value),
        enforcement_mode=settings.mfa_enforcement_mode,
        locked_until=record.locked_until if record else None,
    )


@router.post(
    "/mfa/enroll/start",
    response_model=MFAEnrollStartResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def mfa_enroll_start(
    payload: PasswordReauthRequest,
    response: Response,
    current_user: User = Depends(get_user_for_mfa_enrollment),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not verify_password(payload.password, current_user.password_hash):
        await record_audit_event(
            db,
            SecurityAuditEventType.MFA_ENROLLMENT_FAILED.value,
            user_id=current_user.id,
            payload={"reason": "invalid_password"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password is incorrect")
    try:
        started = await mfa_service.start_enrollment(db, current_user, settings)
    except mfa_service.MFAError as exc:
        raise _mfa_http_error(exc) from exc
    response.headers["Cache-Control"] = "no-store"
    return MFAEnrollStartResponse(
        secret=started.secret,
        otpauth_uri=started.otpauth_uri,
        qr_svg_data_uri=started.qr_svg_data_uri,
    )


@router.post(
    "/mfa/enroll/verify",
    response_model=MFARecoveryCodesResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def mfa_enroll_verify(
    payload: MFAEnrollVerifyRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_user_for_mfa_enrollment),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        codes = await mfa_service.confirm_enrollment(db, current_user, payload.code, settings)
    except mfa_service.MFAError as exc:
        raise _mfa_http_error(exc) from exc

    # The user just proved possession of the authenticator: keep THIS session
    # (upgraded to MFA-verified) and revoke every other session.
    current = await find_refresh_record(db, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    keep = None
    if current is not None and current.user_id == current_user.id and current.revoked_at is None:
        current.mfa_verified = True
        keep = current.id
    revoked = await revoke_other_sessions(db, current_user.id, keep)
    await record_audit_event(
        db,
        AuthAuditEventType.SESSIONS_REVOKED.value,
        user_id=current_user.id,
        payload={"revoked": revoked, "reason": "mfa_enabled"},
    )

    result = MFARecoveryCodesResponse(recovery_codes=codes)
    if keep is None:
        # Strict-mode enrollment (no session yet) or cookie missing: issue a
        # fresh MFA-verified session.
        access_token, raw_refresh = await issue_token_pair(
            db,
            current_user,
            settings,
            user_agent=request.headers.get("user-agent"),
            mfa_verified=True,
        )
        _set_refresh_cookie(response, raw_refresh, settings)
        result.access_token = access_token
    else:
        from app.core.security import create_access_token

        result.access_token = create_access_token(
            current_user.id, current_user.role, settings, mfa=True
        )
    result.user = user_public(current_user, True, settings)
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/mfa/recovery-codes/regenerate",
    response_model=MFARecoveryCodesResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def mfa_regenerate_codes(
    payload: MFARegenerateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        codes = await mfa_service.regenerate_recovery_codes(
            db, current_user, password=payload.password, code=payload.code, settings=settings
        )
    except mfa_service.MFAError as exc:
        raise _mfa_http_error(exc) from exc
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return MFARecoveryCodesResponse(recovery_codes=codes)


@router.post(
    "/mfa/disable",
    response_model=SessionsRevokedResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def mfa_disable(
    payload: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        await mfa_service.disable_mfa(
            db,
            current_user,
            password=payload.password,
            code=payload.code,
            recovery_code=payload.recovery_code,
            settings=settings,
        )
    except mfa_service.MFAError as exc:
        raise _mfa_http_error(exc) from exc
    await db.commit()
    return SessionsRevokedResponse(revoked=0)
