"""Seed SLA policies (idempotent).

Run after migrations:
  python scripts/seed_sla_policies.py
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import dispose_engine, get_session_factory
from app.models.enums import TicketPriority
from app.models.sla_policy import SlaPolicy

DEFAULT_POLICIES = [
    {
        "priority": TicketPriority.LOW,
        "response_time_minutes": 480,
        "resolution_time_minutes": 2880,
    },
    {
        "priority": TicketPriority.MEDIUM,
        "response_time_minutes": 240,
        "resolution_time_minutes": 1440,
    },
    {
        "priority": TicketPriority.HIGH,
        "response_time_minutes": 60,
        "resolution_time_minutes": 480,
    },
    {
        "priority": TicketPriority.CRITICAL,
        "response_time_minutes": 15,
        "resolution_time_minutes": 240,
    },
]


async def main() -> None:
    get_settings.cache_clear()
    session_factory = get_session_factory()

    async with session_factory() as session:
        for policy_data in DEFAULT_POLICIES:
            result = await session.execute(
                select(SlaPolicy).where(SlaPolicy.priority == policy_data["priority"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(SlaPolicy(**policy_data))
                print(f"Seeded SLA policy: {policy_data['priority'].value}")
            else:
                existing.response_time_minutes = policy_data["response_time_minutes"]
                existing.resolution_time_minutes = policy_data["resolution_time_minutes"]
                print(f"Updated SLA policy: {policy_data['priority'].value}")
        await session.commit()

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
