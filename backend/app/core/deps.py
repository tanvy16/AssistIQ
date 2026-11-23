from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import MFA_ENROLL_TOKEN, decode_access_token, decode_purpose_token
from app.models.enums import UserRole
from app.models.security import UserMFA
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def _load_user_with_mfa(db: AsyncSession, user_id: UUID) -> tuple[User | None, bool]:
    # Single round trip: user row plus MFA flag.
    row = (
        await db.execute(
            select(User, UserMFA.enabled)
            .outerjoin(UserMFA, UserMFA.user_id == User.id)
            .where(User.id == user_id)
        )
    ).first()
    if row is None:
        return None, False
    return row[0], bool(row[1])


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        role = UserRole(payload["role"])
        token_mfa = bool(payload.get("mfa", False))
    except Exception as exc:
        raise _unauthorized("Invalid or expired access token") from exc

    user, mfa_enabled = await _load_user_with_mfa(db, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    if user.role != role:
        raise _unauthorized("Invalid or expired access token")

    # An account with MFA enabled only accepts tokens minted after a passed
    # second-factor challenge. Blocks bypass via tokens issued before enrollment.
    if mfa_enabled and not token_mfa:
        raise _unauthorized("MFA verification required")

    settings = get_settings()
    if (
        settings.mfa_enforcement_mode == "strict"
        and not mfa_enabled
        and settings.role_requires_mfa(user.role.value)
    ):
        raise _unauthorized("MFA enrollment required for your role")

    # Used by the 403 handler to attribute permission-denied audit events.
    request.state.auth_user_id = user.id
    request.state.mfa_enabled = mfa_enabled
    return user


async def get_user_for_mfa_enrollment(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Accept a normal access token OR a strict-mode enrollment token.

    The enrollment token is only valid for the MFA enrollment endpoints.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        user_id = decode_purpose_token(credentials.credentials, MFA_ENROLL_TOKEN)
    except Exception:
        return await get_current_user(request, credentials, db)
    user, _ = await _load_user_with_mfa(db, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    request.state.auth_user_id = user.id
    request.state.via_enrollment_token = True
    return user


def require_roles(*roles: UserRole):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
