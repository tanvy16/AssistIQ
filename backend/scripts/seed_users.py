"""Seed development users from environment variables.

Required env vars (set in backend/.env or shell):
  SEED_EMPLOYEE_EMAIL, SEED_EMPLOYEE_PASSWORD
  SEED_AGENT_EMAIL, SEED_AGENT_PASSWORD
  SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD

Optional display names:
  SEED_EMPLOYEE_DISPLAY_NAME (default: Employee)
  SEED_AGENT_DISPLAY_NAME (default: Agent)
  SEED_ADMIN_DISPLAY_NAME (default: Admin)
"""

import asyncio
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.database import dispose_engine, get_session_factory
from app.models.enums import UserRole
from app.services.auth_service import ensure_seed_user


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


async def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()

    seeds = [
        (
            _require_env("SEED_EMPLOYEE_EMAIL"),
            _require_env("SEED_EMPLOYEE_PASSWORD"),
            UserRole.EMPLOYEE,
            os.getenv("SEED_EMPLOYEE_DISPLAY_NAME", "Employee"),
        ),
        (
            _require_env("SEED_AGENT_EMAIL"),
            _require_env("SEED_AGENT_PASSWORD"),
            UserRole.AGENT,
            os.getenv("SEED_AGENT_DISPLAY_NAME", "Agent"),
        ),
        (
            _require_env("SEED_ADMIN_EMAIL"),
            _require_env("SEED_ADMIN_PASSWORD"),
            UserRole.ADMIN,
            os.getenv("SEED_ADMIN_DISPLAY_NAME", "Admin"),
        ),
    ]

    session_factory = get_session_factory()
    async with session_factory() as session:
        for email, password, role, display_name in seeds:
            user = await ensure_seed_user(
                session,
                email=email,
                password=password,
                role=role,
                display_name=display_name,
            )
            print(f"Seeded {role.value}: {user.email} ({user.id})")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
