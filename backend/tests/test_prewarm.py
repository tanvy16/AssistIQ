"""Isolated tests for Ollama prewarm. Mock HTTP only. No Neon, no Ollama."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import (
    PREWARM_CONNECT_TIMEOUT_SECONDS,
    PREWARM_POOL_TIMEOUT_SECONDS,
    PREWARM_TIMEOUT_SECONDS,
    PREWARM_WRITE_TIMEOUT_SECONDS,
    _prewarm_local_llm,
    lifespan,
)

_GENERATE_URL = "http://127.0.0.1:11434/api/generate"


def _settings(**overrides):
    values = {
        "LLM_PROVIDER": "ollama",
        "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
        "LLM_DEFAULT_MODEL": "llama3.2:latest",
        "APP_ENV": "development",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _allow_prewarm(monkeypatch) -> None:
    monkeypatch.setattr("app.main._in_test_environment", lambda _settings: False)


def _install_client(monkeypatch, *, response=None, error=None):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout=None, **_kwargs):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            captured["posted"] = True
            if error is not None:
                raise error
            return response

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    return captured


def _http_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", _GENERATE_URL)
    return httpx.Response(status_code, request=request)


def _assert_not_completed(caplog) -> None:
    assert "Local LLM keep-alive prewarm completed" not in caplog.text


@pytest.fixture
def caplog_info(caplog):
    caplog.set_level(logging.INFO, logger="assistiq")
    return caplog


@pytest.mark.asyncio
async def test_successful_http_response_logs_completed(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    captured = _install_client(monkeypatch, response=_http_response(200))

    await _prewarm_local_llm(_settings())

    assert captured.get("posted") is True
    assert captured["url"] == _GENERATE_URL
    assert captured["json"]["model"] == "llama3.2:latest"
    assert captured["json"]["keep_alive"] == "30m"
    assert captured["json"]["stream"] is False
    assert "Local LLM keep-alive prewarm completed" in caplog_info.text
    assert "Local LLM prewarm skipped" not in caplog_info.text


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 404, 500])
async def test_http_error_status_is_failure(monkeypatch, caplog_info, status_code):
    _allow_prewarm(monkeypatch)
    captured = _install_client(monkeypatch, response=_http_response(status_code))

    await _prewarm_local_llm(_settings())

    assert captured.get("posted") is True
    _assert_not_completed(caplog_info)
    assert f"Local LLM prewarm skipped (http_status={status_code})" in caplog_info.text


@pytest.mark.asyncio
async def test_read_timeout_is_failure(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    request = httpx.Request("POST", _GENERATE_URL)
    _install_client(monkeypatch, error=httpx.ReadTimeout("timed out", request=request))

    await _prewarm_local_llm(_settings())

    _assert_not_completed(caplog_info)
    assert "Local LLM prewarm skipped (timeout)" in caplog_info.text


@pytest.mark.asyncio
async def test_connection_error_is_failure(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    request = httpx.Request("POST", _GENERATE_URL)
    _install_client(
        monkeypatch,
        error=httpx.ConnectError("connection refused", request=request),
    )

    await _prewarm_local_llm(_settings())

    _assert_not_completed(caplog_info)
    assert "Local LLM prewarm skipped (connection_error)" in caplog_info.text


@pytest.mark.asyncio
async def test_unexpected_exception_does_not_raise(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    _install_client(monkeypatch, error=RuntimeError("boom"))

    await _prewarm_local_llm(_settings())

    _assert_not_completed(caplog_info)
    assert "Local LLM prewarm skipped (unexpected_error)" in caplog_info.text


@pytest.mark.asyncio
async def test_non_ollama_provider_does_not_request(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    captured = _install_client(monkeypatch, response=_http_response(200))

    await _prewarm_local_llm(_settings(LLM_PROVIDER="openai"))

    assert captured.get("posted") is None
    assert caplog_info.text == ""


@pytest.mark.asyncio
async def test_test_environment_guard_skips_request(monkeypatch, caplog_info):
    captured = _install_client(monkeypatch, response=_http_response(200))

    await _prewarm_local_llm(_settings())

    assert captured.get("posted") is None
    assert caplog_info.text == ""


@pytest.mark.asyncio
async def test_cancellation_propagates(monkeypatch):
    _allow_prewarm(monkeypatch)
    started = asyncio.Event()

    class HangingClient:
        def __init__(self, timeout=None, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

        async def post(self, url, json=None):
            started.set()
            await asyncio.sleep(3600)

    monkeypatch.setattr("httpx.AsyncClient", HangingClient)

    task = asyncio.create_task(_prewarm_local_llm(_settings()))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_lifespan_cancels_prewarm_on_shutdown(monkeypatch):
    cancelled = {"value": False}
    started = asyncio.Event()

    async def hanging_prewarm(_settings):
        started.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled["value"] = True
            raise

    monkeypatch.setattr("app.main._ensure_ai_models_on_startup", AsyncMock())
    monkeypatch.setattr("app.main._prewarm_local_llm", hanging_prewarm)
    monkeypatch.setattr("app.main.dispose_engine", AsyncMock())
    monkeypatch.setattr(
        "app.main.config.get_settings",
        lambda: SimpleNamespace(LLM_PROVIDER="ollama", APP_ENV="development"),
    )

    async with lifespan(SimpleNamespace()):
        await asyncio.wait_for(started.wait(), timeout=2)

    assert cancelled["value"] is True


@pytest.mark.asyncio
async def test_prewarm_timeout_allows_cold_load_window(monkeypatch, caplog_info):
    _allow_prewarm(monkeypatch)
    captured = _install_client(monkeypatch, response=_http_response(200))

    await _prewarm_local_llm(_settings())

    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == PREWARM_TIMEOUT_SECONDS
    assert timeout.read == 45.0
    assert timeout.connect == PREWARM_CONNECT_TIMEOUT_SECONDS
    assert timeout.write == PREWARM_WRITE_TIMEOUT_SECONDS
    assert timeout.pool == PREWARM_POOL_TIMEOUT_SECONDS
    assert timeout.connect < timeout.read
    assert "Local LLM keep-alive prewarm completed" in caplog_info.text


def test_prewarm_timeout_constant_is_bounded():
    assert PREWARM_TIMEOUT_SECONDS == 45.0
    assert PREWARM_CONNECT_TIMEOUT_SECONDS == 5.0
    assert PREWARM_CONNECT_TIMEOUT_SECONDS < PREWARM_TIMEOUT_SECONDS
