from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.rate_limit import rate_limit
from app.models.enums import AuthAuditEventType, UserRole
from app.models.security import UserMFA
from app.models.user import User
from app.schemas.auth import AdminMFAResetRequest, SessionsRevokedResponse
from app.services import mfa_service
from app.services.audit_service import record_audit_event
from app.services.auth_service import revoke_other_sessions

router = APIRouter(prefix="/users")


class UserDirectoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    display_name: str | None
    is_active: bool
    mfa_enabled: bool = False
    mfa_required: bool = False


class UserListResponse(BaseModel):
    items: list[UserDirectoryItem]
    total: int


@router.get("", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    settings: Settings = Depends(get_settings),
) -> UserListResponse:
    result = await db.execute(
        select(User, UserMFA.enabled)
        .outerjoin(UserMFA, UserMFA.user_id == User.id)
        .order_by(User.created_at.desc())
    )
    items = []
    for user, mfa_enabled in result.all():
        item = UserDirectoryItem.model_validate(user)
        item.mfa_enabled = bool(mfa_enabled)
        item.mfa_required = settings.role_requires_mfa(user.role.value)
        items.append(item)
    return UserListResponse(items=items, total=len(items))


@router.post(
    "/{user_id}/mfa/reset",
    response_model=SessionsRevokedResponse,
    dependencies=[Depends(rate_limit("mfa"))],
)
async def admin_reset_user_mfa(
    user_id: UUID,
    payload: AdminMFAResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> SessionsRevokedResponse:
    """Recovery for a user who lost their authenticator AND recovery codes.

    Requires the admin's own password. Removes the user's MFA and signs out all
    of their sessions so they must sign in again and re-enroll.
    """
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        await mfa_service.admin_reset_mfa(
            db, admin=admin, admin_password=payload.admin_password, target=target
        )
    except mfa_service.MFAReauthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except mfa_service.MFAError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    revoked = await revoke_other_sessions(db, target.id, None)
    await record_audit_event(
        db,
        AuthAuditEventType.SESSIONS_REVOKED.value,
        user_id=target.id,
        payload={"revoked": revoked, "reason": "admin_mfa_reset", "by": str(admin.id)},
    )
    await db.commit()
    return SessionsRevokedResponse(revoked=revoked)
