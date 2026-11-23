"""Admin-only AI observability APIs. Aggregates existing telemetry; never returns secrets."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.services.observability_service import get_observability_service

router = APIRouter(prefix="/observability", tags=["observability"])

admin_only = require_roles(UserRole.ADMIN)


def _window(
    range_key: str,
    start: datetime | None,
    end: datetime | None,
):
    try:
        return get_observability_service().parse_window(range_key, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/summary")
async def observability_summary(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return await get_observability_service().summary(db, _window(range, start, end))


@router.get("/models")
async def observability_models(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    rows = await get_observability_service().model_usage(db, _window(range, start, end))
    return {"items": [row.model_dump() for row in rows]}


@router.get("/usage")
async def observability_usage(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return await get_observability_service().usage_breakdown(db, _window(range, start, end))


@router.get("/tokens")
async def observability_tokens(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().tokens(db, _window(range, start, end))).model_dump()


@router.get("/cost")
async def observability_cost(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().cost(db, _window(range, start, end))).model_dump()


@router.get("/latency")
async def observability_latency(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return await get_observability_service().latency(db, _window(range, start, end))


@router.get("/rag")
async def observability_rag(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().rag(db, _window(range, start, end))).model_dump()


@router.get("/chat")
async def observability_chat(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().chat(db, _window(range, start, end))).model_dump()


@router.get("/it-workflows")
async def observability_it_workflows(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().it_workflows(db, _window(range, start, end))).model_dump()


@router.get("/password-resets")
async def observability_password_resets(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    return (await get_observability_service().password_resets(db, _window(range, start, end))).model_dump()


@router.get("/evaluations")
async def observability_evaluations(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    rows = await get_observability_service().evaluations(db, _window(range, start, end))
    return {"items": [row.model_dump() for row in rows]}


@router.get("/anomalies")
async def observability_anomalies(
    range: str = Query("7d", alias="range"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(admin_only),
):
    items = await get_observability_service().anomalies(db, _window(range, start, end))
    return {"items": [item.model_dump() for item in items]}
