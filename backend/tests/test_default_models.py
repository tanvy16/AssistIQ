"""Isolated tests for default AI registry initialization. No Neon / real DB."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.default_models import (
    DEFAULT_MODEL_KEYS,
    DEFAULT_MODELS,
    ensure_default_ai_models,
    reseed_default_ai_models,
)
from app.ai.enums import AIModelType
from app.models.ai import AIModelRegistry


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class _FakeSession:
    def __init__(self, store: dict[str, SimpleNamespace]):
        self.store = store
        self.added: list[AIModelRegistry] = []
        self.commit_calls = 0

    async def execute(self, stmt):
        compiled = stmt.compile()
        key = next(
            (value for value in compiled.params.values() if isinstance(value, str)),
            None,
        )
        return _FakeResult(self.store.get(key))

    def add(self, obj: AIModelRegistry) -> None:
        self.added.append(obj)
        self.store[obj.model_key] = obj

    async def commit(self) -> None:
        self.commit_calls += 1


class _FakeFactory:
    def __init__(self, session: _FakeSession):
        self.session = session

    def __call__(self) -> _FakeFactory:
        return self

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _session_pair(initial: dict[str, SimpleNamespace] | None = None):
    store = dict(initial or {})
    session = _FakeSession(store)
    return store, session, _FakeFactory(session)


@pytest.mark.asyncio
async def test_ensure_inserts_four_default_keys_when_empty():
    store, session, factory = _session_pair()

    result = await ensure_default_ai_models(session_factory=factory)

    assert sorted(result["inserted"]) == sorted(DEFAULT_MODEL_KEYS)
    assert result["skipped"] == []
    assert {row.model_key for row in session.added} == set(DEFAULT_MODEL_KEYS)
    assert session.commit_calls == 1
    assert all(getattr(row, "enabled", True) is True for row in session.added)


@pytest.mark.asyncio
async def test_ensure_second_call_does_not_duplicate():
    store, session, factory = _session_pair()
    await ensure_default_ai_models(session_factory=factory)
    first_added = list(session.added)

    result = await ensure_default_ai_models(session_factory=factory)

    assert result["inserted"] == []
    assert sorted(result["skipped"]) == sorted(DEFAULT_MODEL_KEYS)
    assert session.added == first_added
    assert len(store) == 4


@pytest.mark.asyncio
async def test_ensure_preserves_disabled_flag():
    existing = SimpleNamespace(
        model_key="ollama-llama3.2",
        model_type=AIModelType.LLM,
        provider="ollama",
        model_name="llama3.2:latest",
        capabilities=["generation"],
        config_metadata={"description": "custom"},
        enabled=False,
    )
    store, session, factory = _session_pair({"ollama-llama3.2": existing})

    result = await ensure_default_ai_models(session_factory=factory)

    assert "ollama-llama3.2" in result["skipped"]
    assert existing.enabled is False
    assert all(row.model_key != "ollama-llama3.2" for row in session.added)


@pytest.mark.asyncio
async def test_ensure_preserves_custom_provider_name_capabilities_and_metadata():
    existing = SimpleNamespace(
        model_key="openai-gpt4o-mini",
        model_type=AIModelType.LLM,
        provider="azure",
        model_name="gpt-4o-custom",
        capabilities=["generation", "custom"],
        config_metadata={"endpoint": "https://example.test", "description": "admin"},
        enabled=True,
    )
    store, session, factory = _session_pair({"openai-gpt4o-mini": existing})

    await ensure_default_ai_models(session_factory=factory)

    assert existing.provider == "azure"
    assert existing.model_name == "gpt-4o-custom"
    assert existing.capabilities == ["generation", "custom"]
    assert existing.config_metadata == {
        "endpoint": "https://example.test",
        "description": "admin",
    }


@pytest.mark.asyncio
async def test_reseed_overwrites_existing_default_key():
    existing = SimpleNamespace(
        model_key="ollama-llama3.2",
        model_type=AIModelType.LLM,
        provider="custom",
        model_name="changed",
        capabilities=["generation"],
        config_metadata={"description": "old"},
        enabled=False,
    )
    store, session, factory = _session_pair({"ollama-llama3.2": existing})

    result = await reseed_default_ai_models(session_factory=factory)

    spec = next(item for item in DEFAULT_MODELS if item["model_key"] == "ollama-llama3.2")
    assert "ollama-llama3.2" in result["updated"]
    assert existing.provider == spec["provider"]
    assert existing.model_name == spec["model_name"]
    assert existing.capabilities == spec["capabilities"]
    assert existing.config_metadata == spec["config_metadata"]
    assert existing.enabled is True


@pytest.mark.asyncio
async def test_startup_skips_when_pytest_current_test(monkeypatch):
    from app.main import _ensure_ai_models_on_startup

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_default_models.py::test")
    settings = SimpleNamespace(APP_ENV="development")
    probe = AsyncMock()
    monkeypatch.setattr("app.ai.default_models.ensure_default_ai_models", probe)

    await _ensure_ai_models_on_startup(settings)

    probe.assert_not_called()


@pytest.mark.asyncio
async def test_startup_skips_when_app_env_test(monkeypatch):
    from app.main import _ensure_ai_models_on_startup

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    settings = SimpleNamespace(APP_ENV="test")
    probe = AsyncMock()
    monkeypatch.setattr("app.ai.default_models.ensure_default_ai_models", probe)

    await _ensure_ai_models_on_startup(settings)

    probe.assert_not_called()


@pytest.mark.asyncio
async def test_startup_runs_ensure_outside_test_env(monkeypatch):
    from app.main import _ensure_ai_models_on_startup

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    settings = SimpleNamespace(APP_ENV="development")
    probe = AsyncMock(return_value={"inserted": ["ollama-llama3.2"], "skipped": []})
    monkeypatch.setattr("app.ai.default_models.ensure_default_ai_models", probe)

    await _ensure_ai_models_on_startup(settings)

    probe.assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_failure_and_continues(monkeypatch, caplog):
    import logging

    from app.main import _ensure_ai_models_on_startup

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    settings = SimpleNamespace(APP_ENV="development")
    probe = AsyncMock(side_effect=RuntimeError("connection refused"))
    monkeypatch.setattr("app.ai.default_models.ensure_default_ai_models", probe)

    with caplog.at_level(logging.WARNING, logger="assistiq"):
        await _ensure_ai_models_on_startup(settings)

    probe.assert_awaited_once()
    assert any("initialization failed" in message for message in caplog.messages)
