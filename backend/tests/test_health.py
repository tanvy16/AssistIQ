import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_does_not_require_database(monkeypatch):
    """Liveness endpoint should work without a configured DATABASE_URL."""
    from app.core.config import Settings

    class TestSettings(Settings):
        DATABASE_URL: str = (
            "postgresql+asyncpg://test:test@localhost/test?sslmode=require"
        )
        JWT_SECRET_KEY: str = "test-jwt-secret-key-at-least-32-chars-long"

    from app.core import config as config_module
    from app.core.database import dispose_engine
    import app.main as main_module

    monkeypatch.setattr(config_module, "get_settings", lambda: TestSettings())
    main_module._application = None

    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    await dispose_engine()
    main_module._application = None


@pytest.mark.asyncio
async def test_readiness_check(client):
    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }
