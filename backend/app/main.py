from contextlib import asynccontextmanager
import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core import config
from app.core.database import dispose_engine
from app.core.logging import configure_logging
from app.core.security_headers import SecurityHeadersMiddleware

_application: FastAPI | None = None
logger = logging.getLogger("assistiq")

# Prewarm-only; chat/retrieval keep LLM_TIMEOUT_SECONDS.
PREWARM_TIMEOUT_SECONDS = 45.0
PREWARM_CONNECT_TIMEOUT_SECONDS = 5.0
PREWARM_WRITE_TIMEOUT_SECONDS = 10.0
PREWARM_POOL_TIMEOUT_SECONDS = 5.0


def json_safe(value: Any) -> Any:
    """Coerce Pydantic error payloads so 422 responses never include raw exceptions."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# Keys removed from 422 payloads: "input" echoes the submitted value (which can
# be a password or OTP), "url" is noise.
_VALIDATION_ERROR_DROP_KEYS = frozenset({"input", "url"})


def sanitize_validation_errors(errors: list[Any]) -> list[Any]:
    cleaned: list[Any] = []
    for error in errors:
        if isinstance(error, dict):
            error = {k: v for k, v in error.items() if k not in _VALIDATION_ERROR_DROP_KEYS}
        cleaned.append(json_safe(error))
    return cleaned


def _in_test_environment(settings) -> bool:
    import os

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return settings.APP_ENV == "test"


async def _ensure_ai_models_on_startup(settings) -> None:
    """Insert missing default registry rows. Never force-upserts existing keys."""
    if _in_test_environment(settings):
        logger.info("AI model registry initialization skipped (test environment)")
        return
    try:
        from app.ai.default_models import ensure_default_ai_models

        result = await ensure_default_ai_models()
        logger.info(
            "AI model registry initialization completed",
            extra={
                "inserted": result.get("inserted"),
                "skipped": result.get("skipped"),
            },
        )
    except Exception:
        logger.warning(
            "AI model registry initialization failed; continuing startup",
            exc_info=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = config.get_settings()
    await _ensure_ai_models_on_startup(settings)
    prewarm_task = asyncio.create_task(_prewarm_local_llm(settings))
    try:
        yield
    finally:
        prewarm_task.cancel()
        try:
            await prewarm_task
        except asyncio.CancelledError:
            pass
        try:
            from app.ai.adapters.llm import close_llm_http_client

            await close_llm_http_client()
        except Exception:
            pass
        await dispose_engine()


async def _prewarm_local_llm(settings) -> None:
    if settings.LLM_PROVIDER.lower() != "ollama":
        return
    if _in_test_environment(settings):
        return
    if not getattr(settings, "LLM_PREWARM_ENABLED", True):
        logger.info("Local LLM prewarm disabled (LLM_PREWARM_ENABLED=false)")
        return

    import httpx

    timeout = httpx.Timeout(
        connect=PREWARM_CONNECT_TIMEOUT_SECONDS,
        read=PREWARM_TIMEOUT_SECONDS,
        write=PREWARM_WRITE_TIMEOUT_SECONDS,
        pool=PREWARM_POOL_TIMEOUT_SECONDS,
    )
    try:
        root = settings.LLM_BASE_URL.rstrip("/").removesuffix("/v1")
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{root}/api/generate",
                json={
                    "model": settings.LLM_DEFAULT_MODEL,
                    "prompt": "ok",
                    "keep_alive": "30m",
                    "stream": False,
                },
            )
            response.raise_for_status()
        logger.info("Local LLM keep-alive prewarm completed")
    except asyncio.CancelledError:
        raise
    except httpx.TimeoutException:
        logger.info("Local LLM prewarm skipped (timeout)")
    except httpx.ConnectError:
        logger.info("Local LLM prewarm skipped (connection_error)")
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        logger.info("Local LLM prewarm skipped (http_status=%s)", status_code)
    except httpx.HTTPError:
        logger.info("Local LLM prewarm skipped (http_error)")
    except Exception:
        logger.info("Local LLM prewarm skipped (unexpected_error)")


async def _audit_permission_denied(request: Request, detail: Any) -> None:
    """Record a 403 in the audit log. Never blocks or alters the response."""
    try:
        from app.core.database import get_session_factory
        from app.models.enums import SecurityAuditEventType
        from app.services.audit_service import record_audit_event

        user_id = getattr(request.state, "auth_user_id", None)
        async with get_session_factory()() as session:
            await record_audit_event(
                session,
                SecurityAuditEventType.PERMISSION_DENIED.value,
                user_id=user_id,
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "reason": str(detail)[:200],
                },
            )
            await session.commit()
    except Exception:
        logger.warning("Could not record permission-denied audit event", exc_info=True)


def create_app() -> FastAPI:
    global _application
    if _application is not None:
        return _application

    settings = config.get_settings()
    configure_logging(settings.APP_ENV)

    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        title="AssistIQ API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 403:
            await _audit_permission_denied(request, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": sanitize_validation_errors(list(exc.errors()))},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, _exc: Exception):
        logger.exception("Unhandled server error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    _application = app
    return app


app = create_app()
