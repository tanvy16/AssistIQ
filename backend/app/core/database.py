import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Awaitable, Callable, TypeVar

from fastapi import Request

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.db_errors import build_db_diagnostic, sanitize_error_message
from app.core.db_url import prepare_asyncpg_url

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_read_session_factory: async_sessionmaker[AsyncSession] | None = None

T = TypeVar("T")
READ_ONLY_METHODS = frozenset({"GET", "HEAD"})


def create_engine(settings: Settings) -> AsyncEngine:
    database_url, connect_args = prepare_asyncpg_url(settings.DATABASE_URL)
    kwargs: dict = {
        "echo": False,
        "connect_args": connect_args,
    }
    in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST")) or settings.APP_ENV == "test"
    if in_pytest:
        # Avoid stale asyncpg connections across pytest event loops.
        kwargs["poolclass"] = NullPool
    else:
        # Neon is ~250 ms away from the demo machine, so every network round
        # trip matters. pool_pre_ping cost one extra round trip per request;
        # instead recycle connections before Neon's 5-minute idle suspend can
        # close them, so a pooled connection is never stale when checked out.
        kwargs["pool_recycle"] = 240
        # Sized so the admin observability page (12 parallel requests, some
        # fanning out read queries) reuses warm connections instead of opening
        # new TLS connections on every load.
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 10
        kwargs["pool_timeout"] = 30
    return create_async_engine(database_url, **kwargs)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings())
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


def get_read_session_factory() -> async_sessionmaker[AsyncSession]:
    """Sessions in AUTOCOMMIT: no BEGIN/ROLLBACK round trips.

    Under PostgreSQL's default READ COMMITTED isolation each statement already
    sees its own snapshot, so read results are identical to a transaction.
    """
    global _read_session_factory
    if _read_session_factory is None:
        _read_session_factory = async_sessionmaker(
            get_engine().execution_options(isolation_level="AUTOCOMMIT"),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _read_session_factory


async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[assignment]
    # GET/HEAD handlers only read; skip the transaction round trips for them.
    # Writes (POST/PATCH/PUT/DELETE) keep normal transactional sessions.
    if request is not None and request.method in READ_ONLY_METHODS:
        session_factory = get_read_session_factory()
    else:
        session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def run_parallel_reads(*readers: Callable[[AsyncSession], Awaitable[Any]]) -> list[Any]:
    """Run independent read-only queries concurrently, one pooled session each.

    Total time becomes roughly the slowest query instead of the sum of all of
    them, which matters when each round trip to the database costs ~250 ms.
    """
    factory = get_read_session_factory()

    async def run(reader: Callable[[AsyncSession], Awaitable[Any]]) -> Any:
        async with factory() as session:
            return await reader(session)

    return list(await asyncio.gather(*(run(reader) for reader in readers)))


async def check_database_connection() -> tuple[bool, dict | None]:
    from sqlalchemy import text

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        diagnostic = build_db_diagnostic(exc)
        logger.error(
            "Database readiness check failed (%s): %s",
            diagnostic["error_category"],
            diagnostic["error_message"],
        )
        return False, diagnostic


async def dispose_engine() -> None:
    global _engine, _session_factory, _read_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        _read_session_factory = None
