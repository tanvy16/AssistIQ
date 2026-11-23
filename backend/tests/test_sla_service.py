from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.enums import TicketPriority
from app.models.sla_policy import SlaPolicy
from app.services.sla_service import calculate_sla_due_at, get_sla_policy


@pytest.mark.asyncio
async def test_calculate_sla_due_at_from_policy(db_session, sla_policies):
    policy = await get_sla_policy(db_session, TicketPriority.HIGH)
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    due_at = calculate_sla_due_at(policy, created_at)
    assert due_at == created_at + timedelta(minutes=policy.resolution_time_minutes)


@pytest.mark.asyncio
async def test_sla_policies_seeded_for_all_priorities(db_session, sla_policies):
    result = await db_session.execute(select(SlaPolicy))
    policies = result.scalars().all()
    assert len(policies) == 4
