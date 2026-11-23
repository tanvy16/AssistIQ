import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.core.deps import require_roles
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
async def test_user(db_session):
    user = User(
        email=_unique_email("employee"),
        password_hash=hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
        display_name="Test Employee",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def test_agent(db_session):
    user = User(
        email=_unique_email("agent"),
        password_hash=hash_password("AgentPass123!"),
        role=UserRole.AGENT,
        display_name="Test Agent",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_login_returns_access_token_and_sets_refresh_cookie(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass123!"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == test_user.email
    assert payload["user"]["role"] == "employee"
    assert "assistiq_refresh" in response.cookies


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword1!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_me_requires_bearer_token(client, test_user):
    unauthenticated = await client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass123!"},
    )
    access_token = login.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == test_user.email
    assert me.json()["role"] == "employee"


@pytest.mark.asyncio
async def test_refresh_rotates_cookie_and_returns_new_access_token(client, test_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass123!"},
    )
    first_refresh = login.cookies.get("assistiq_refresh")
    first_access = login.json()["access_token"]

    refresh = await client.post(
        "/api/v1/auth/refresh",
        cookies={"assistiq_refresh": first_refresh},
    )
    assert refresh.status_code == 200
    second_access = refresh.json()["access_token"]
    second_refresh = refresh.cookies.get("assistiq_refresh")

    assert second_access
    assert second_access != first_access
    assert second_refresh
    assert second_refresh != first_refresh

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second_access}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, test_user, db_session):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass123!"},
    )
    refresh_cookie = login.cookies.get("assistiq_refresh")

    logout = await client.post(
        "/api/v1/auth/logout",
        cookies={"assistiq_refresh": refresh_cookie},
    )
    assert logout.status_code == 200
    assert logout.json()["status"] == "ok"

    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh",
        cookies={"assistiq_refresh": refresh_cookie},
    )
    assert refresh_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_require_roles_allows_agent(test_agent):
    dep = require_roles(UserRole.AGENT, UserRole.ADMIN)
    allowed = await dep(current_user=test_agent)
    assert allowed.id == test_agent.id


@pytest.mark.asyncio
async def test_require_roles_blocks_employee(test_user):
    dep = require_roles(UserRole.AGENT, UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await dep(current_user=test_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_login_records_audit_event(client, test_user, db_session):
    from sqlalchemy import select

    from app.models.audit_event import AuditEvent
    from app.models.enums import AuthAuditEventType

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass123!"},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.user_id == test_user.id,
            AuditEvent.event_type == AuthAuditEventType.LOGIN.value,
        )
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.payload["email"] == test_user.email


@pytest.mark.asyncio
async def test_failed_login_records_audit_event(client, test_user, db_session):
    from sqlalchemy import select

    from app.models.audit_event import AuditEvent
    from app.models.enums import AuthAuditEventType

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword1!"},
    )
    assert response.status_code == 401

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == AuthAuditEventType.LOGIN_FAILED.value,
        )
    )
    events = result.scalars().all()
    assert any(event.payload.get("email") == test_user.email for event in events)


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401
