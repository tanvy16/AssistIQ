from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, text, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
    UserRole,
)
from app.models.ticket import Ticket, TicketComment, TicketEvent
from app.models.user import User
from app.services.sla_service import SlaPolicyNotFoundError, calculate_sla_due_at_for_priority


class TicketError(Exception):
    pass


class TicketNotFoundError(TicketError):
    pass


class TicketAccessDeniedError(TicketError):
    pass


class InvalidStatusTransitionError(TicketError):
    pass


class TicketClosedError(TicketError):
    pass


VALID_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
    },
    TicketStatus.IN_PROGRESS: {TicketStatus.PENDING, TicketStatus.RESOLVED},
    TicketStatus.PENDING: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: set(),
}

QUEUE_STATUSES = {
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.PENDING,
}


async def _next_ticket_number(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT nextval('ticket_number_seq')"))
    sequence_value = int(result.scalar_one())
    return f"TICK-{sequence_value:05d}"


async def _append_event(
    db: AsyncSession,
    ticket_id: UUID,
    actor_id: UUID | None,
    event_type: TicketEventType,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict | None = None,
) -> TicketEvent:
    event = TicketEvent(
        ticket_id=ticket_id,
        actor_id=actor_id,
        event_type=event_type.value,
        old_value=old_value,
        new_value=new_value,
        event_metadata=metadata,
    )
    db.add(event)
    await db.flush()
    return event


def _can_access_ticket(user: User, ticket: Ticket) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.EMPLOYEE:
        return ticket.requester_id == user.id
    if user.role == UserRole.AGENT:
        if ticket.assignee_id == user.id:
            return True
        return ticket.assignee_id is None and ticket.status in QUEUE_STATUSES
    return False


def _employee_list_filter(user: User):
    return Ticket.requester_id == user.id


def _agent_list_filter(user: User, scope: str | None):
    assigned = Ticket.assignee_id == user.id
    queue = (Ticket.assignee_id.is_(None)) & (Ticket.status.in_(QUEUE_STATUSES))
    if scope == "assigned":
        return assigned
    if scope == "queue":
        return queue
    return or_(assigned, queue)


async def create_ticket(
    db: AsyncSession,
    user: User,
    title: str,
    description: str,
    category: TicketCategory,
    priority: TicketPriority,
) -> Ticket:
    if user.role != UserRole.EMPLOYEE:
        raise TicketAccessDeniedError("Only employees can create tickets")

    now = datetime.now(UTC)
    sla_due_at = await calculate_sla_due_at_for_priority(db, priority, now)
    ticket_number = await _next_ticket_number(db)

    ticket = Ticket(
        ticket_number=ticket_number,
        requester_id=user.id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        status=TicketStatus.OPEN,
        sla_due_at=sla_due_at,
    )
    db.add(ticket)
    await db.flush()
    await _append_event(
        db,
        ticket.id,
        user.id,
        TicketEventType.CREATED,
        new_value=TicketStatus.OPEN.value,
        metadata={"priority": priority.value, "category": category.value},
    )
    await db.commit()
    return await get_ticket(db, user, ticket.id)


async def ensure_ticket_for_conversation(
    db: AsyncSession,
    *,
    actor: User,
    conversation_id: UUID,
    requester_id: UUID,
    title: str,
    description: str,
    category: TicketCategory = TicketCategory.OTHER,
    priority: TicketPriority = TicketPriority.MEDIUM,
) -> Ticket:
    """Create or reuse the open-queue ticket linked to a chat conversation.

    Does not commit; the caller owns the transaction. REST ticket create remains
    employee-only. Chat escalation may be performed by the conversation owner
    or by an agent/admin on their behalf.
    """
    if actor.role == UserRole.EMPLOYEE and actor.id != requester_id:
        raise TicketAccessDeniedError("You can only escalate your own conversations")
    if actor.role not in {UserRole.EMPLOYEE, UserRole.AGENT, UserRole.ADMIN}:
        raise TicketAccessDeniedError("Insufficient permissions")

    existing = await db.execute(
        select(Ticket)
        .where(Ticket.conversation_id == conversation_id)
        .order_by(Ticket.created_at.asc())
        .limit(1)
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found

    now = datetime.now(UTC)
    try:
        sla_due_at = await calculate_sla_due_at_for_priority(db, priority, now)
    except SlaPolicyNotFoundError as exc:
        raise TicketError("SLA policy is not configured; a support ticket cannot be created.") from exc

    ticket_number = await _next_ticket_number(db)
    ticket = Ticket(
        ticket_number=ticket_number,
        requester_id=requester_id,
        title=(title or "Chat support request").strip()[:200],
        description=description.strip()[:8000],
        category=category,
        priority=priority,
        status=TicketStatus.OPEN,
        sla_due_at=sla_due_at,
        conversation_id=conversation_id,
    )
    db.add(ticket)
    await db.flush()
    await _append_event(
        db,
        ticket.id,
        actor.id,
        TicketEventType.CREATED,
        new_value=TicketStatus.OPEN.value,
        metadata={
            "priority": priority.value,
            "category": category.value,
            "source": "chat",
            "conversation_id": str(conversation_id),
        },
    )
    return ticket


async def list_tickets(
    db: AsyncSession,
    user: User,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    assignee_id: UUID | None = None,
    requester_id: UUID | None = None,
    scope: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = select(Ticket)
    count_query = select(func.count()).select_from(Ticket)

    if user.role == UserRole.EMPLOYEE:
        role_filter = _employee_list_filter(user)
        query = query.where(role_filter)
        count_query = count_query.where(role_filter)
    elif user.role == UserRole.AGENT:
        role_filter = _agent_list_filter(user, scope)
        query = query.where(role_filter)
        count_query = count_query.where(role_filter)
    elif assignee_id is not None:
        query = query.where(Ticket.assignee_id == assignee_id)
        count_query = count_query.where(Ticket.assignee_id == assignee_id)
    if requester_id is not None and user.role == UserRole.ADMIN:
        query = query.where(Ticket.requester_id == requester_id)
        count_query = count_query.where(Ticket.requester_id == requester_id)

    if status is not None:
        query = query.where(Ticket.status == status)
        count_query = count_query.where(Ticket.status == status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if category is not None:
        query = query.where(Ticket.category == category)
        count_query = count_query.where(Ticket.category == category)

    total = int((await db.execute(count_query)).scalar_one())
    result = await db.execute(
        query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_ticket(db: AsyncSession, user: User, ticket_id: UUID) -> Ticket:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.comments),
            selectinload(Ticket.events),
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise TicketNotFoundError()
    if not _can_access_ticket(user, ticket):
        raise TicketAccessDeniedError()
    return ticket


def _ensure_not_closed(ticket: Ticket) -> None:
    if ticket.status == TicketStatus.CLOSED:
        raise TicketClosedError("Closed tickets cannot be modified")


def _validate_status_transition(
    current: TicketStatus, new_status: TicketStatus
) -> None:
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition from {current.value} to {new_status.value}"
        )


async def _load_users_for_ticket(
    db: AsyncSession, ticket: Ticket
) -> tuple[User | None, User | None]:
    requester = await db.get(User, ticket.requester_id)
    assignee = await db.get(User, ticket.assignee_id) if ticket.assignee_id else None
    return requester, assignee


async def update_ticket(
    db: AsyncSession,
    user: User,
    ticket_id: UUID,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
) -> Ticket:
    ticket = await get_ticket(db, user, ticket_id)
    _ensure_not_closed(ticket)

    if user.role == UserRole.EMPLOYEE:
        raise TicketAccessDeniedError("Employees cannot update ticket status")

    if status is not None:
        _validate_status_transition(ticket.status, status)
        if user.role == UserRole.AGENT and ticket.assignee_id is None:
            # An agent working an unassigned queue ticket takes ownership.
            # Without this, moving it out of the queue (e.g. to resolved)
            # committed the change but then answered 403, because agents can
            # only see queue tickets or tickets assigned to them.
            ticket.assignee_id = user.id
            await _append_event(
                db,
                ticket.id,
                user.id,
                TicketEventType.ASSIGNED,
                old_value=None,
                new_value=str(user.id),
            )
        old_status = ticket.status.value
        ticket.status = status
        if status == TicketStatus.RESOLVED and ticket.resolved_at is None:
            ticket.resolved_at = datetime.now(UTC)
        if status == TicketStatus.IN_PROGRESS and ticket.resolved_at is not None:
            ticket.resolved_at = None
        await _append_event(
            db,
            ticket.id,
            user.id,
            TicketEventType.STATUS_CHANGED,
            old_value=old_status,
            new_value=status.value,
        )

    if priority is not None and priority != ticket.priority:
        if user.role not in {UserRole.AGENT, UserRole.ADMIN}:
            raise TicketAccessDeniedError()
        old_priority = ticket.priority.value
        ticket.priority = priority
        ticket.sla_due_at = await calculate_sla_due_at_for_priority(
            db, priority, ticket.created_at
        )
        await _append_event(
            db,
            ticket.id,
            user.id,
            TicketEventType.PRIORITY_CHANGED,
            old_value=old_priority,
            new_value=priority.value,
        )

    await db.commit()
    return await get_ticket(db, user, ticket_id)


async def assign_ticket(
    db: AsyncSession,
    user: User,
    ticket_id: UUID,
    assignee_id: UUID | None,
) -> Ticket:
    if user.role not in {UserRole.AGENT, UserRole.ADMIN}:
        raise TicketAccessDeniedError()

    ticket = await get_ticket(db, user, ticket_id)
    _ensure_not_closed(ticket)

    if assignee_id is not None:
        assignee = await db.get(User, assignee_id)
        if assignee is None or assignee.role not in {UserRole.AGENT, UserRole.ADMIN}:
            raise TicketError("Assignee must be an active agent or admin")
        if not assignee.is_active:
            raise TicketError("Assignee must be active")

        if user.role == UserRole.AGENT and assignee_id != user.id:
            raise TicketAccessDeniedError("Agents can only claim tickets for themselves")

        old_assignee = str(ticket.assignee_id) if ticket.assignee_id else None
        ticket.assignee_id = assignee_id
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        await _append_event(
            db,
            ticket.id,
            user.id,
            TicketEventType.ASSIGNED,
            old_value=old_assignee,
            new_value=str(assignee_id),
        )
    else:
        if user.role == UserRole.AGENT:
            raise TicketAccessDeniedError("Agents cannot unassign tickets")
        old_assignee = str(ticket.assignee_id) if ticket.assignee_id else None
        ticket.assignee_id = None
        await _append_event(
            db,
            ticket.id,
            user.id,
            TicketEventType.UNASSIGNED,
            old_value=old_assignee,
            new_value=None,
        )

    await db.commit()
    return await get_ticket(db, user, ticket_id)


async def add_comment(
    db: AsyncSession,
    user: User,
    ticket_id: UUID,
    body: str,
) -> TicketComment:
    ticket = await get_ticket(db, user, ticket_id)

    comment = TicketComment(
        ticket_id=ticket.id,
        author_id=user.id,
        body=body,
    )
    db.add(comment)
    await db.flush()
    await _append_event(
        db,
        ticket.id,
        user.id,
        TicketEventType.COMMENT_ADDED,
        metadata={"comment_id": str(comment.id)},
    )
    await db.commit()
    await db.refresh(comment)
    return comment


async def list_ticket_events(
    db: AsyncSession,
    user: User,
    ticket_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[TicketEvent], int]:
    await get_ticket(db, user, ticket_id)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    count_query = (
        select(func.count())
        .select_from(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
    )
    total = int((await db.execute(count_query)).scalar_one())

    result = await db.execute(
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


def _visibility_filter(user: User, scope: str | None = None):
    if user.role == UserRole.EMPLOYEE:
        return _employee_list_filter(user)
    if user.role == UserRole.AGENT:
        return _agent_list_filter(user, scope)
    return true()


async def ticket_stats(db: AsyncSession, user: User) -> dict:
    visibility = _visibility_filter(user)
    now = datetime.now(UTC)
    sla_horizon = now + timedelta(hours=1)
    active = Ticket.status.in_(QUEUE_STATUSES)

    stmt = select(
        func.count().label("total"),
        func.coalesce(func.sum(case((Ticket.status == TicketStatus.OPEN, 1), else_=0)), 0).label("open"),
        func.coalesce(
            func.sum(case((Ticket.status == TicketStatus.IN_PROGRESS, 1), else_=0)), 0
        ).label("in_progress"),
        func.coalesce(func.sum(case((Ticket.status == TicketStatus.PENDING, 1), else_=0)), 0).label(
            "pending"
        ),
        func.coalesce(func.sum(case((Ticket.status == TicketStatus.RESOLVED, 1), else_=0)), 0).label(
            "resolved"
        ),
        func.coalesce(func.sum(case((Ticket.status == TicketStatus.CLOSED, 1), else_=0)), 0).label(
            "closed"
        ),
        func.coalesce(func.sum(case((Ticket.assignee_id == user.id, 1), else_=0)), 0).label(
            "assigned_to_me"
        ),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(Ticket.assignee_id.is_(None), Ticket.status.in_(QUEUE_STATUSES)),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("unassigned_queue"),
        func.coalesce(
            func.sum(case((and_(active, Ticket.sla_due_at <= sla_horizon), 1), else_=0)),
            0,
        ).label("sla_at_risk"),
        func.coalesce(
            func.sum(case((and_(active, Ticket.sla_due_at < now), 1), else_=0)),
            0,
        ).label("sla_breached"),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Ticket.resolved_at.is_not(None),
                            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("resolved_with_sla"),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Ticket.resolved_at.is_not(None),
                            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                            Ticket.resolved_at <= Ticket.sla_due_at,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("resolved_on_time"),
    ).where(visibility)

    row = (await db.execute(stmt)).one()
    resolved_with_sla = int(row.resolved_with_sla or 0)
    resolved_on_time = int(row.resolved_on_time or 0)
    compliance = (
        round((resolved_on_time / resolved_with_sla) * 100, 1) if resolved_with_sla else None
    )

    if user.role == UserRole.AGENT:
        unassigned_queue = await _count_tickets(db, _agent_list_filter(user, "queue"))
        assigned_to_me = await _count_tickets(db, _agent_list_filter(user, "assigned"))
    elif user.role == UserRole.ADMIN:
        unassigned_queue = await _count_tickets(
            db, (Ticket.assignee_id.is_(None)) & (Ticket.status.in_(QUEUE_STATUSES))
        )
        assigned_to_me = await _count_tickets(db, Ticket.assignee_id == user.id)
    else:
        unassigned_queue = 0
        assigned_to_me = int(row.assigned_to_me or 0)

    return {
        "total": int(row.total or 0),
        "open": int(row.open or 0),
        "in_progress": int(row.in_progress or 0),
        "pending": int(row.pending or 0),
        "resolved": int(row.resolved or 0),
        "closed": int(row.closed or 0),
        "assigned_to_me": assigned_to_me,
        "unassigned_queue": unassigned_queue,
        "sla_at_risk": int(row.sla_at_risk or 0),
        "sla_breached": int(row.sla_breached or 0),
        "sla_compliance_pct": compliance,
    }


async def _count_tickets(db: AsyncSession, clause) -> int:
    result = await db.execute(select(func.count()).select_from(Ticket).where(clause))
    return int(result.scalar_one())


async def recent_ticket_activity(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 12,
) -> list[tuple[TicketEvent, Ticket, User | None]]:
    visibility = _visibility_filter(user)
    stmt = (
        select(TicketEvent, Ticket, User)
        .join(Ticket, Ticket.id == TicketEvent.ticket_id)
        .outerjoin(User, User.id == TicketEvent.actor_id)
        .where(visibility)
        .order_by(TicketEvent.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]
