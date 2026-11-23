from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
    UserRole,
)
from app.models.ticket import Ticket, TicketComment, TicketEvent
from app.models.user import User
from app.schemas.ticket import (
    TicketAssignRequest,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketCreate,
    TicketEventResponse,
    TicketListItem,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
    UserSummary,
)
from app.schemas.dashboard import TicketStats
from app.services.ticket_service import (
    InvalidStatusTransitionError,
    TicketAccessDeniedError,
    TicketClosedError,
    TicketError,
    TicketNotFoundError,
    add_comment,
    assign_ticket,
    create_ticket,
    get_ticket,
    list_ticket_events,
    list_tickets,
    ticket_stats,
    update_ticket,
)

router = APIRouter(prefix="/tickets")


def _user_summary(user: User | None) -> UserSummary | None:
    if user is None:
        return None
    return UserSummary.model_validate(user)


async def _load_users_map(
    db: AsyncSession, *user_ids: UUID | None
) -> dict[UUID, User]:
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(ids)))
    return {user.id: user for user in result.scalars().all()}


async def _ticket_to_list_item(
    db: AsyncSession, ticket: Ticket
) -> TicketListItem:
    items = await _tickets_to_list_items(db, [ticket])
    return items[0]


async def _tickets_to_list_items(
    db: AsyncSession, tickets: list[Ticket]
) -> list[TicketListItem]:
    users = await _load_users_map(
        db,
        *[ticket.requester_id for ticket in tickets],
        *[ticket.assignee_id for ticket in tickets],
    )
    return [
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
            requester=_user_summary(users.get(ticket.requester_id)),
            assignee=_user_summary(users.get(ticket.assignee_id)) if ticket.assignee_id else None,
        )
        for ticket in tickets
    ]


async def _ticket_to_response(db: AsyncSession, ticket: Ticket) -> TicketResponse:
    user_ids: set[UUID] = {ticket.requester_id}
    if ticket.assignee_id:
        user_ids.add(ticket.assignee_id)
    for comment in ticket.comments:
        user_ids.add(comment.author_id)
    for event in ticket.events:
        if event.actor_id:
            user_ids.add(event.actor_id)

    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {user.id: user for user in result.scalars().all()}

    comments = [
        TicketCommentResponse(
            id=comment.id,
            ticket_id=comment.ticket_id,
            author=_user_summary(users[comment.author_id]),  # type: ignore[arg-type]
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        for comment in ticket.comments
    ]
    events = [
        TicketEventResponse(
            id=event.id,
            ticket_id=event.ticket_id,
            actor=_user_summary(users.get(event.actor_id)) if event.actor_id else None,
            event_type=event.event_type,
            old_value=event.old_value,
            new_value=event.new_value,
            event_metadata=event.event_metadata,
            created_at=event.created_at,
        )
        for event in ticket.events
    ]

    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        sla_due_at=ticket.sla_due_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        requester=_user_summary(users[ticket.requester_id]),  # type: ignore[arg-type]
        assignee=_user_summary(users.get(ticket.assignee_id))
        if ticket.assignee_id
        else None,
        comments=comments,
        events=events,
    )


def _handle_ticket_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TicketNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if isinstance(exc, TicketAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, InvalidStatusTransitionError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, TicketClosedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, TicketError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise exc


@router.get("", response_model=TicketListResponse)
async def get_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    assignee_id: UUID | None = None,
    requester_id: UUID | None = None,
    scope: str | None = Query(
        default=None,
        description="Agent scope: queue, assigned, or all (default all permitted)",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tickets, total = await list_tickets(
            db,
            current_user,
            status=status_filter,
            priority=priority,
            category=category,
            assignee_id=assignee_id if current_user.role == UserRole.ADMIN else None,
            requester_id=requester_id if current_user.role == UserRole.ADMIN else None,
            scope=scope,
            page=page,
            page_size=page_size,
        )
    except TicketAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    items = await _tickets_to_list_items(db, tickets)
    return TicketListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/stats", response_model=TicketStats)
async def get_ticket_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ticket_stats(db, current_user)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def post_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = await create_ticket(
            db,
            current_user,
            payload.title,
            payload.description,
            payload.category,
            payload.priority,
        )
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return await _ticket_to_response(db, ticket)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_by_id(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = await get_ticket(db, current_user, ticket_id)
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return await _ticket_to_response(db, ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def patch_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = await update_ticket(
            db,
            current_user,
            ticket_id,
            status=payload.status,
            priority=payload.priority,
        )
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return await _ticket_to_response(db, ticket)


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def post_assign_ticket(
    ticket_id: UUID,
    payload: TicketAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignee_id = payload.assignee_id or current_user.id
    try:
        ticket = await assign_ticket(db, current_user, ticket_id, assignee_id)
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return await _ticket_to_response(db, ticket)


@router.post("/{ticket_id}/unassign", response_model=TicketResponse)
async def post_unassign_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = await assign_ticket(db, current_user, ticket_id, None)
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return await _ticket_to_response(db, ticket)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_ticket_comment(
    ticket_id: UUID,
    payload: TicketCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        comment = await add_comment(db, current_user, ticket_id, payload.body)
        author = await db.get(User, comment.author_id)
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc
    return TicketCommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author=_user_summary(author),  # type: ignore[arg-type]
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get("/{ticket_id}/events", response_model=list[TicketEventResponse])
async def get_ticket_events(
    ticket_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        events, _total = await list_ticket_events(
            db, current_user, ticket_id, page=page, page_size=page_size
        )
        actor_ids = {event.actor_id for event in events if event.actor_id}
        users = await _load_users_map(db, *actor_ids)
    except TicketError as exc:
        raise _handle_ticket_error(exc) from exc

    return [
        TicketEventResponse(
            id=event.id,
            ticket_id=event.ticket_id,
            actor=_user_summary(users.get(event.actor_id)) if event.actor_id else None,
            event_type=event.event_type,
            old_value=event.old_value,
            new_value=event.new_value,
            event_metadata=event.event_metadata,
            created_at=event.created_at,
        )
        for event in events
    ]
