from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TicketPriority
from app.models.sla_policy import SlaPolicy


class SlaPolicyNotFoundError(Exception):
    pass


async def get_sla_policy(
    db: AsyncSession, priority: TicketPriority
) -> SlaPolicy:
    result = await db.execute(
        select(SlaPolicy).where(SlaPolicy.priority == priority)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise SlaPolicyNotFoundError(f"No SLA policy for priority {priority.value}")
    return policy


def calculate_sla_due_at(
    policy: SlaPolicy, created_at: datetime | None = None
) -> datetime:
    base = created_at or datetime.now(UTC)
    return base + timedelta(minutes=policy.resolution_time_minutes)


async def calculate_sla_due_at_for_priority(
    db: AsyncSession,
    priority: TicketPriority,
    created_at: datetime | None = None,
) -> datetime:
    policy = await get_sla_policy(db, priority)
    return calculate_sla_due_at(policy, created_at)
