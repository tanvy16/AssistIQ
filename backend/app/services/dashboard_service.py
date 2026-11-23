"""Operational dashboard aggregates from existing ticket, user, KB, and AI tables."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIInferenceTelemetry
from app.models.enums import KnowledgeDocumentStatus, UserRole
from app.models.knowledge import KnowledgeDocument
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    AIUsageStats,
    DashboardSummary,
    KnowledgeStats,
    ServiceHealth,
    TicketStats,
    UserStats,
)
from app.schemas.ticket import TicketListItem, UserSummary
from app.services.ticket_service import list_tickets, recent_ticket_activity, ticket_stats


def _user_summary(user: User | None) -> UserSummary | None:
    if user is None:
        return None
    return UserSummary.model_validate(user)


def _activity_summary(event_type: str, ticket_number: str, actor_name: str | None) -> str:
    actor = actor_name or "System"
    labels = {
        "ticket.created": f"{ticket_number} created",
        "ticket.assigned": f"{ticket_number} assigned",
        "ticket.unassigned": f"{ticket_number} returned to queue",
        "ticket.status_changed": f"{ticket_number} status updated",
        "ticket.priority_changed": f"{ticket_number} priority updated",
        "ticket.comment_added": f"{ticket_number} comment added",
    }
    base = labels.get(event_type, f"{ticket_number} {event_type.replace('ticket.', '').replace('_', ' ')}")
    return f"{base} · {actor}"


async def build_dashboard_summary(db: AsyncSession, actor: User) -> DashboardSummary:
    from app.core.database import run_parallel_reads

    list_scope = "assigned" if actor.role == UserRole.AGENT else None

    async def recent_tickets_with_people(session: AsyncSession):
        tickets, _total = await list_tickets(session, actor, scope=list_scope, page=1, page_size=8)
        user_ids = {t.requester_id for t in tickets} | {t.assignee_id for t in tickets if t.assignee_id}
        people: dict = {}
        if user_ids:
            result = await session.execute(select(User).where(User.id.in_(user_ids)))
            people = {user.id: user for user in result.scalars().all()}
        return tickets, people

    readers = [
        lambda session: ticket_stats(session, actor),
        recent_tickets_with_people,
        lambda session: recent_ticket_activity(session, actor, limit=12),
    ]
    if actor.role == UserRole.ADMIN:
        readers += [_knowledge_stats, _user_stats, _ai_usage_stats]
    # Independent aggregates run concurrently (each on its own pooled
    # connection); the request now costs about the slowest query, not the sum.
    results = await run_parallel_reads(*readers)
    stats = TicketStats.model_validate(results[0])
    tickets, users_by_id = results[1]
    activity_rows = results[2]

    recent_tickets = [
        TicketListItem(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            sla_due_at=ticket.sla_due_at,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            requester=_user_summary(users_by_id.get(ticket.requester_id)),
            assignee=_user_summary(users_by_id.get(ticket.assignee_id)) if ticket.assignee_id else None,
        )
        for ticket in tickets
    ]

    recent_activity = [
        ActivityItem(
            id=event.id,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            event_type=event.event_type,
            actor_name=actor_user.display_name or actor_user.email if actor_user else None,
            created_at=event.created_at,
            summary=_activity_summary(
                event.event_type,
                ticket.ticket_number,
                actor_user.display_name or actor_user.email if actor_user else None,
            ),
        )
        for event, ticket, actor_user in activity_rows
    ]

    health = ServiceHealth(api="ok", database="connected")

    knowledge = users = ai = None
    if actor.role == UserRole.ADMIN:
        knowledge, users, ai = results[3], results[4], results[5]

    return DashboardSummary(
        tickets=stats,
        recent_tickets=recent_tickets,
        recent_activity=recent_activity,
        health=health,
        knowledge=knowledge,
        users=users,
        ai=ai,
    )


async def _knowledge_stats(db: AsyncSession) -> KnowledgeStats:
    stmt = select(
        func.count().label("total"),
        func.coalesce(
            func.sum(case_eq(KnowledgeDocument.status, KnowledgeDocumentStatus.PUBLISHED)), 0
        ).label("published"),
        func.coalesce(
            func.sum(case_eq(KnowledgeDocument.status, KnowledgeDocumentStatus.DRAFT)), 0
        ).label("draft"),
        func.coalesce(
            func.sum(case_eq(KnowledgeDocument.status, KnowledgeDocumentStatus.ARCHIVED)), 0
        ).label("archived"),
    )
    row = (await db.execute(stmt)).one()
    return KnowledgeStats(
        total=int(row.total or 0),
        published=int(row.published or 0),
        draft=int(row.draft or 0),
        archived=int(row.archived or 0),
    )


async def _user_stats(db: AsyncSession) -> UserStats:
    from sqlalchemy import and_, case

    stmt = select(
        func.count().label("total"),
        func.coalesce(func.sum(case((User.is_active.is_(True), 1), else_=0)), 0).label("active"),
        func.coalesce(func.sum(case((User.role == UserRole.AGENT, 1), else_=0)), 0).label("agents"),
        func.coalesce(
            func.sum(
                case((and_(User.role == UserRole.AGENT, User.is_active.is_(True)), 1), else_=0)
            ),
            0,
        ).label("active_agents"),
        func.coalesce(func.sum(case((User.role == UserRole.EMPLOYEE, 1), else_=0)), 0).label(
            "employees"
        ),
        func.coalesce(func.sum(case((User.role == UserRole.ADMIN, 1), else_=0)), 0).label("admins"),
    )
    row = (await db.execute(stmt)).one()
    return UserStats(
        total=int(row.total or 0),
        active=int(row.active or 0),
        agents=int(row.agents or 0),
        active_agents=int(row.active_agents or 0),
        employees=int(row.employees or 0),
        admins=int(row.admins or 0),
    )


async def _ai_usage_stats(db: AsyncSession) -> AIUsageStats:
    from sqlalchemy import case

    window_start = datetime.now(UTC) - timedelta(days=7)
    stmt = select(
        func.count().label("request_count"),
        func.coalesce(func.sum(case((AIInferenceTelemetry.success.is_(True), 1), else_=0)), 0).label(
            "successful"
        ),
        func.coalesce(func.sum(case((AIInferenceTelemetry.success.is_(False), 1), else_=0)), 0).label(
            "failed"
        ),
        func.sum(AIInferenceTelemetry.total_tokens).label("total_tokens"),
    ).where(AIInferenceTelemetry.created_at >= window_start)
    row = (await db.execute(stmt)).one()
    return AIUsageStats(
        request_count=int(row.request_count or 0),
        successful=int(row.successful or 0),
        failed=int(row.failed or 0),
        total_tokens=int(row.total_tokens) if row.total_tokens is not None else None,
    )


def case_eq(column, value):
    from sqlalchemy import case

    return case((column == value, 1), else_=0)
