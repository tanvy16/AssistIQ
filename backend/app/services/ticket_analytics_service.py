"""Ticket analytics computed from persisted rows only.

Every number is a SQL aggregate over tickets / escalations. Days with no rows
are zero-filled explicitly (and flagged by `has_data`) so the UI can show an
honest empty state instead of a fabricated trend.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Escalation
from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.models.ticket import Ticket

ALLOWED_WINDOWS = (7, 14, 30, 90)
ACTIVE_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING)
SLA_AT_RISK_HORIZON = timedelta(hours=1)  # matches ticket_service.ticket_stats


def _day_bucket(column):
    return func.date_trunc("day", func.timezone("UTC", column))


async def _daily_counts(db: AsyncSession, column, start: datetime, *extra) -> dict[date, int]:
    bucket = _day_bucket(column).label("day")
    stmt = (
        select(bucket, func.count().label("n"))
        .where(column >= start, *extra)
        .group_by(bucket)
    )
    rows = (await db.execute(stmt)).all()
    return {row.day.date(): int(row.n) for row in rows}


async def ticket_analytics(db: AsyncSession, days: int) -> dict:
    if days not in ALLOWED_WINDOWS:
        raise ValueError(f"days must be one of {ALLOWED_WINDOWS}")
    now = datetime.now(UTC)
    today = now.date()
    first_day = today - timedelta(days=days - 1)
    start = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC)

    by_status = dict(
        (await db.execute(select(Ticket.status, func.count()).group_by(Ticket.status))).all()
    )
    by_priority = dict(
        (
            await db.execute(
                select(Ticket.priority, func.count())
                .where(Ticket.status.in_(ACTIVE_STATUSES))
                .group_by(Ticket.priority)
            )
        ).all()
    )
    by_category = dict(
        (
            await db.execute(
                select(Ticket.category, func.count())
                .where(Ticket.created_at >= start)
                .group_by(Ticket.category)
            )
        ).all()
    )

    active = Ticket.status.in_(ACTIVE_STATUSES)
    sla_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(case((and_(active, Ticket.sla_due_at < now), 1), else_=0)), 0).label("breached"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    active,
                                    Ticket.sla_due_at >= now,
                                    Ticket.sla_due_at <= now + SLA_AT_RISK_HORIZON,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("at_risk"),
                func.coalesce(
                    func.sum(case((and_(active, Ticket.sla_due_at > now + SLA_AT_RISK_HORIZON), 1), else_=0)), 0
                ).label("on_track"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Ticket.resolved_at.is_not(None),
                                    Ticket.resolved_at >= start,
                                    Ticket.resolved_at <= Ticket.sla_due_at,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("resolved_within"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Ticket.resolved_at.is_not(None),
                                    Ticket.resolved_at >= start,
                                    Ticket.resolved_at > Ticket.sla_due_at,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("resolved_late"),
            )
        )
    ).one()

    created = await _daily_counts(db, Ticket.created_at, start)
    resolved = await _daily_counts(db, Ticket.resolved_at, start, Ticket.resolved_at.is_not(None))
    escalations = await _daily_counts(db, Escalation.created_at, start)
    chat_tickets = await _daily_counts(
        db, Ticket.created_at, start, Ticket.conversation_id.is_not(None)
    )

    series = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        series.append(
            {
                "date": day.isoformat(),
                "created": created.get(day, 0),
                "resolved": resolved.get(day, 0),
                "escalations": escalations.get(day, 0),
                "chat_tickets": chat_tickets.get(day, 0),
            }
        )

    resolved_in_window = int(sla_row.resolved_within) + int(sla_row.resolved_late)
    return {
        "window_days": days,
        "window_start": start.isoformat(),
        "generated_at": now.isoformat(),
        "status": {s.value: int(by_status.get(s, 0)) for s in TicketStatus},
        "active_by_priority": {p.value: int(by_priority.get(p, 0)) for p in TicketPriority},
        "created_by_category": {c.value: int(by_category.get(c, 0)) for c in TicketCategory},
        "sla": {
            "active_on_track": int(sla_row.on_track),
            "active_at_risk": int(sla_row.at_risk),
            "active_breached": int(sla_row.breached),
            "resolved_within_sla": int(sla_row.resolved_within),
            "resolved_after_sla": int(sla_row.resolved_late),
            # None (not 0 %) when nothing was resolved in the window.
            "compliance_pct": (
                round(100.0 * int(sla_row.resolved_within) / resolved_in_window, 1)
                if resolved_in_window
                else None
            ),
        },
        "totals": {
            "created": sum(created.values()),
            "resolved": sum(resolved.values()),
            "escalations": sum(escalations.values()),
            "chat_tickets": sum(chat_tickets.values()),
        },
        "daily": series,
        "has_data": bool(created or resolved or escalations),
    }
