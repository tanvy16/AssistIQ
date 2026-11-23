import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

pytest_plugins = ["tests.ai_fixtures"]

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"

TEST_JWT_SECRET = "test-jwt-secret-key-at-least-32-chars-long"


def _read_env_value(key: str) -> str:
    value = os.getenv(key, "")
    if value:
        return value
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return ""


def _is_loopback_url(url: str) -> bool:
    from urllib.parse import urlparse

    try:
        return urlparse(url).hostname in {"127.0.0.1", "localhost", "::1"}
    except ValueError:
        return False


def _has_valid_database_url() -> bool:
    url = _read_env_value("DATABASE_URL")
    if not url or not url.startswith("postgresql+asyncpg://"):
        return False
    if url.startswith("postgresql+asyncpg://USER:"):
        return False
    if _is_loopback_url(url):
        # Disposable local database (see backend/scripts/run_isolated_tests.ps1).
        return True
    if "sslmode=require" not in url:
        return False
    # DB-backed fixtures commit and delete rows. Never run them against a shared
    # (non-loopback) database such as the team's Neon project unless explicitly
    # opted in.
    return os.getenv("ASSISTIQ_ALLOW_SHARED_DB_TESTS") == "1"


def _skip_reason_for_database() -> str:
    url = _read_env_value("DATABASE_URL")
    if url and not _is_loopback_url(url):
        return (
            "DB-backed test skipped: DATABASE_URL is not a loopback database. "
            "Run backend/scripts/run_isolated_tests.ps1 (disposable Docker Postgres) "
            "instead of writing to a shared database."
        )
    return "DATABASE_URL not configured"


def _has_jwt_secret() -> bool:
    secret = _read_env_value("JWT_SECRET_KEY")
    return bool(secret and len(secret.strip()) >= 32)


def _reset_app_state() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.main as main_module

    main_module._application = None

    try:
        from app.adapters.chroma import reset_chroma_adapter
        from app.agents.graphs.chat_graph import reset_chat_graph
        from app.agents.graphs.it_request_graph import reset_it_request_graph
        from app.ai.registry import reset_adapter_factory
        from app.execution.adapter import reset_execution_adapter
        from app.runbooks.registry import reset_runbook_registry
        from app.services.ai_model_service import reset_ai_model_service
        from app.services.chat_service import reset_chat_service
        from app.services.embedding_service import reset_embedding_service
        from app.services.it_request_service import reset_it_request_service
        from app.agents.graphs.password_reset_graph import reset_password_reset_graph
        from app.iam.adapter import reset_iam_adapter
        from app.services.password_reset_service import reset_password_reset_service
        from app.services.knowledge_base_service import reset_knowledge_service
        from app.services.observability_service import reset_observability_service
        from app.core.rate_limit import reset_rate_limiter

        reset_chroma_adapter()
        reset_embedding_service()
        reset_knowledge_service()
        reset_observability_service()
        reset_rate_limiter()
        reset_adapter_factory()
        reset_ai_model_service()
        reset_chat_service()
        reset_chat_graph()
        reset_it_request_graph()
        reset_it_request_service()
        reset_password_reset_service()
        reset_password_reset_graph()
        reset_execution_adapter()
        reset_iam_adapter()
        reset_runbook_registry()
    except ImportError:
        pass


# Fixtures that open a real database session. Several of them delete whole tables
# in teardown (knowledge documents, conversations, IT requests, AI telemetry), so a
# test that requests any of them must be skipped at collection time -- before any
# fixture setup/teardown can run -- whenever the database is not the disposable
# loopback test database.
DB_BACKED_FIXTURES = frozenset(
    {
        "client",
        "db_session",
        "ai_models",
        "it_catalogs",
        "cleanup_knowledge",
        "cleanup_chat",
    }
)


def pytest_collection_modifyitems(config, items):
    if _has_valid_database_url():
        return
    marker = pytest.mark.skip(reason=_skip_reason_for_database())
    for item in items:
        if DB_BACKED_FIXTURES.intersection(getattr(item, "fixturenames", ())):
            item.add_marker(marker)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    if not _has_valid_database_url():
        pytest.skip(_skip_reason_for_database())
    if not _has_jwt_secret():
        pytest.skip("JWT_SECRET_KEY not configured in backend/.env")

    _reset_app_state()

    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    _reset_app_state()


@pytest.fixture
async def db_session():
    if not _has_valid_database_url():
        pytest.skip(_skip_reason_for_database())

    _reset_app_state()

    from app.core.database import dispose_engine, get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session

    await dispose_engine()
    _reset_app_state()


# --- Phase 3 ticket fixtures ---

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.models.enums import TicketPriority, UserRole
from app.models.sla_policy import SlaPolicy
from app.models.ticket import Ticket
from app.models.user import User

DEFAULT_SLA = [
    (TicketPriority.LOW, 480, 2880),
    (TicketPriority.MEDIUM, 240, 1440),
    (TicketPriority.HIGH, 60, 480),
    (TicketPriority.CRITICAL, 15, 240),
]


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
async def sla_policies(db_session):
    for priority, response_mins, resolution_mins in DEFAULT_SLA:
        result = await db_session.execute(
            select(SlaPolicy).where(SlaPolicy.priority == priority)
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            db_session.add(
                SlaPolicy(
                    priority=priority,
                    response_time_minutes=response_mins,
                    resolution_time_minutes=resolution_mins,
                )
            )
    await db_session.commit()


@pytest.fixture
async def employee_user(db_session):
    user = User(
        email=_unique_email("employee"),
        password_hash=hash_password("EmployeePass123!"),
        role=UserRole.EMPLOYEE,
        display_name="Ticket Employee",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    from app.models.chat import Conversation
    from app.models.it_request import ITRequest
    from app.models.password_reset import PasswordResetRequest

    await db_session.execute(
        delete(PasswordResetRequest).where(
            (PasswordResetRequest.requester_id == user.id)
            | (PasswordResetRequest.target_user_id == user.id)
        )
    )
    await db_session.execute(delete(ITRequest).where(ITRequest.requester_id == user.id))
    await db_session.execute(delete(Ticket).where(Ticket.requester_id == user.id))
    await db_session.execute(delete(Conversation).where(Conversation.user_id == user.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def employee_user_b(db_session):
    user = User(
        email=_unique_email("employee-b"),
        password_hash=hash_password("EmployeePass123!"),
        role=UserRole.EMPLOYEE,
        display_name="Other Employee",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    from app.models.chat import Conversation
    from app.models.it_request import ITRequest
    from app.models.password_reset import PasswordResetRequest

    await db_session.execute(
        delete(PasswordResetRequest).where(
            (PasswordResetRequest.requester_id == user.id)
            | (PasswordResetRequest.target_user_id == user.id)
        )
    )
    await db_session.execute(delete(ITRequest).where(ITRequest.requester_id == user.id))
    await db_session.execute(delete(Ticket).where(Ticket.requester_id == user.id))
    await db_session.execute(delete(Conversation).where(Conversation.user_id == user.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def agent_user(db_session):
    user = User(
        email=_unique_email("agent"),
        password_hash=hash_password("AgentPass123!"),
        role=UserRole.AGENT,
        display_name="Ticket Agent",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    from app.models.it_request import ITRequest
    from app.models.password_reset import PasswordResetRequest

    await db_session.execute(
        delete(PasswordResetRequest).where(
            (PasswordResetRequest.requester_id == user.id)
            | (PasswordResetRequest.target_user_id == user.id)
        )
    )
    await db_session.execute(delete(ITRequest).where(ITRequest.requester_id == user.id))
    await db_session.execute(delete(Ticket).where(Ticket.assignee_id == user.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session):
    user = User(
        email=_unique_email("admin"),
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        display_name="Ticket Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    from app.models.it_request import ITRequest
    from app.models.password_reset import PasswordResetRequest

    await db_session.execute(
        delete(PasswordResetRequest).where(
            (PasswordResetRequest.requester_id == user.id)
            | (PasswordResetRequest.target_user_id == user.id)
        )
    )
    await db_session.execute(delete(ITRequest).where(ITRequest.requester_id == user.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def employee_auth(client, employee_user):
    return await _login(client, employee_user.email, "EmployeePass123!")


@pytest.fixture
async def employee_b_auth(client, employee_user_b):
    return await _login(client, employee_user_b.email, "EmployeePass123!")


@pytest.fixture
async def agent_auth(client, agent_user):
    return await _login(client, agent_user.email, "AgentPass123!")


@pytest.fixture
async def admin_auth(client, admin_user):
    return await _login(client, admin_user.email, "AdminPass123!")


def ticket_payload(**overrides):
    data = {
        "title": "VPN connection failing",
        "description": "Unable to connect to corporate VPN from home network since this morning.",
        "category": "network",
        "priority": "medium",
    }
    data.update(overrides)
    return data
