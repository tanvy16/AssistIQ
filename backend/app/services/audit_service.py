from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    event_type: str,
    user_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event
