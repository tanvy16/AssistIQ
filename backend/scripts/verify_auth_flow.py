"""Manual auth flow verification against a running local API."""

import asyncio
import os
import secrets
import sys
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

API_BASE = "http://127.0.0.1:18765"
MANUAL_EMAIL = os.getenv("MANUAL_AUTH_EMAIL", "manual-verify@example.com")
MANUAL_PASSWORD = os.getenv("MANUAL_AUTH_PASSWORD")


async def ensure_user() -> None:
    if not MANUAL_PASSWORD:
        raise SystemExit("Set MANUAL_AUTH_PASSWORD in the environment")

    from app.core.config import get_settings
    from app.core.database import dispose_engine, get_session_factory
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.services.auth_service import ensure_seed_user, get_user_by_email

    get_settings.cache_clear()
    session_factory = get_session_factory()
    async with session_factory() as session:
        existing = await get_user_by_email(session, MANUAL_EMAIL)
        if existing is not None:
            existing.password_hash = hash_password(MANUAL_PASSWORD)
            existing.is_active = True
            await session.commit()
        else:
            await ensure_seed_user(
                session,
                email=MANUAL_EMAIL,
                password=MANUAL_PASSWORD,
                role=UserRole.EMPLOYEE,
                display_name="Manual Verify",
            )
    await dispose_engine()


async def verify_flow() -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": MANUAL_EMAIL, "password": MANUAL_PASSWORD},
        )
        assert login.status_code == 200, login.text
        access_token = login.json()["access_token"]
        refresh_cookie = login.cookies.get("assistiq_refresh")
        assert refresh_cookie

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me.status_code == 200, me.text
        assert me.json()["email"] == MANUAL_EMAIL
        assert me.json()["role"] == "employee"

        refresh = await client.post(
            "/api/v1/auth/refresh",
            cookies={"assistiq_refresh": refresh_cookie},
        )
        assert refresh.status_code == 200, refresh.text
        new_access = refresh.json()["access_token"]
        new_refresh = refresh.cookies.get("assistiq_refresh")
        assert new_access != access_token
        assert new_refresh != refresh_cookie

        logout = await client.post(
            "/api/v1/auth/logout",
            cookies={"assistiq_refresh": new_refresh},
        )
        assert logout.status_code == 200, logout.text

        refresh_after_logout = await client.post(
            "/api/v1/auth/refresh",
            cookies={"assistiq_refresh": new_refresh},
        )
        assert refresh_after_logout.status_code == 401, refresh_after_logout.text

    print("Manual auth flow verification: PASS")


async def main() -> None:
    await ensure_user()
    await verify_flow()


if __name__ == "__main__":
    if not MANUAL_PASSWORD:
        MANUAL_PASSWORD = secrets.token_urlsafe(16)
        os.environ["MANUAL_AUTH_PASSWORD"] = MANUAL_PASSWORD
    asyncio.run(main())
