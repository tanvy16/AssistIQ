"""Safe local database connectivity check. Does not print credentials."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


async def main() -> int:
    env_path = BACKEND_ROOT / ".env"
    if not env_path.exists():
        print("FAIL: backend/.env is missing.")
        print("Create it from backend/.env.example and set DATABASE_URL to your Neon dev branch URL.")
        return 1

    from app.core.config import get_settings
    from app.core.database import check_database_connection, dispose_engine

    settings = get_settings()
    url = settings.DATABASE_URL
    print("backend/.env: found")
    print(f"driver: {'ok' if url.startswith('postgresql+asyncpg://') else 'invalid'}")
    print(f"sslmode: {'ok' if 'sslmode=require' in url else 'missing'}")
    print(f"placeholder: {'yes' if url.startswith('postgresql+asyncpg://USER:') else 'no'}")

    if url.startswith("postgresql+asyncpg://USER:"):
        print("FAIL: DATABASE_URL is still the placeholder value.")
        return 1

    ready, diagnostic = await check_database_connection()
    await dispose_engine()

    if ready:
        print("PASS: database connection succeeded.")
        return 0

    print("FAIL: database connection failed.")
    if diagnostic:
        print(f"category: {diagnostic['error_category']}")
        print(f"detail: {diagnostic['error_message']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
