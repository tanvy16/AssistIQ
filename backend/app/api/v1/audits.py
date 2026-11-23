"""Admin-only audit event listing. Read-only; never returns secrets."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.audit_event import AuditEvent
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/audits", tags=["audits"])

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "access_token",
    "refresh_token",
    "jwt",
    "api_key",
    "secret",
    "token",
    "authorization",
}


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_value(item)
            for key, item in value.items()
            if str(key).lower() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    # Recursive: sensitive keys are removed at every nesting level.
    if not payload:
        return payload
    return _sanitize_value(payload)


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    event_type: str
    payload: dict[str, Any] | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    event_type: str | None = Query(
        default=None,
        max_length=64,
        description="Exact event type, or a prefix ending in '.' (e.g. 'mfa.', 'auth.')",
    ),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> AuditEventListResponse:
    filters = []
    if event_type:
        if event_type.endswith("."):
            filters.append(AuditEvent.event_type.startswith(event_type, autoescape=True))
        else:
            filters.append(AuditEvent.event_type == event_type)
    total = (
        await db.execute(select(func.count()).select_from(AuditEvent).where(*filters))
    ).scalar_one()
    rows = (
        await db.execute(
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    items = [
        AuditEventResponse(
            id=row.id,
            user_id=row.user_id,
            event_type=row.event_type,
            payload=_sanitize(row.payload),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AuditEventListResponse(items=items, total=int(total or 0), page=page, page_size=page_size)
