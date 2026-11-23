from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_factory
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    CitationResponse,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    EscalationRequest,
    EscalationResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.ai_model_service import (
    AIModelDisabledError,
    AIModelNotFoundError,
    AIModelValidationError,
)
from app.services.chat_service import (
    ChatAccessDeniedError,
    ChatNotFoundError,
    ChatService,
    ChatValidationError,
    get_chat_service,
)

router = APIRouter(prefix="/chat")


def _citation_response(citation) -> CitationResponse:
    metadata = citation.citation_metadata or {}
    return CitationResponse(
        id=citation.id,
        document_id=citation.document_id,
        chunk_id=citation.chunk_id,
        title=citation.title,
        similarity_score=citation.similarity_score,
        category=metadata.get("category"),
    )


def _message_response(message) -> ChatMessageResponse:
    from app.models.chat import ChatMessageRole

    citations: list[CitationResponse] = []
    if message.role == ChatMessageRole.ASSISTANT:
        citations = [_citation_response(c) for c in message.citations]

    return ChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role.value,
        content=message.content,
        model_id=message.model_id,
        latency_ms=message.latency_ms,
        prompt_tokens=message.prompt_tokens,
        completion_tokens=message.completion_tokens,
        total_tokens=message.total_tokens,
        intent=message.intent,
        confidence_state=message.confidence_state.value if message.confidence_state else None,
        citations=citations,
        created_at=message.created_at,
    )


def _handle_chat_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, ChatNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ChatAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(
        exc,
        (
            ChatValidationError,
            AIModelNotFoundError,
            AIModelDisabledError,
            AIModelValidationError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    try:
        conversation = await service.create_conversation(
            db,
            actor=current_user,
            title=payload.title,
            selected_model_id=payload.selected_model_id,
        )
    except Exception as exc:
        raise _handle_chat_errors(exc) from exc
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationListResponse:
    conversations = await service.list_conversations(db, actor=current_user)
    items = [ConversationResponse.model_validate(item) for item in conversations]
    return ConversationListResponse(items=items, total=len(items))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    try:
        conversation = await service.get_conversation(
            db, actor=current_user, conversation_id=conversation_id
        )
    except Exception as exc:
        raise _handle_chat_errors(exc) from exc
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[ChatMessageResponse]:
    try:
        messages = await service.list_messages(
            db, actor=current_user, conversation_id=conversation_id
        )
    except Exception as exc:
        raise _handle_chat_errors(exc) from exc
    return [_message_response(message) for message in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    dependencies=[Depends(rate_limit("chat"))],
)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> SendMessageResponse:
    try:
        user_message, assistant_message = await service.send_message(
            db,
            actor=current_user,
            conversation_id=conversation_id,
            content=payload.content,
            selected_model_id=payload.selected_model_id,
        )
    except Exception as exc:
        raise _handle_chat_errors(exc) from exc
    return SendMessageResponse(
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
    )


def _sse(event: str, data: dict) -> str:
    import json

    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    dependencies=[Depends(rate_limit("chat"))],
)
async def send_message_stream(
    conversation_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    actor_id = current_user.id

    async def event_stream():
        async with get_session_factory()() as stream_db:
            actor = await stream_db.get(User, actor_id)
            if actor is None:
                yield _sse("error", {"detail": "Not authenticated"})
                return
            try:
                async for item in service.send_message_stream(
                    stream_db,
                    actor=actor,
                    conversation_id=conversation_id,
                    content=payload.content,
                    selected_model_id=payload.selected_model_id,
                ):
                    event = item["event"]
                    data = item["data"]
                    if event == "done":
                        data = {
                            "user_message": _message_response(data["user_message"]).model_dump(
                                mode="json"
                            ),
                            "assistant_message": _message_response(
                                data["assistant_message"]
                            ).model_dump(mode="json"),
                        }
                    yield _sse(event, data)
            except Exception as exc:
                http_exc = _handle_chat_errors(exc)
                yield _sse("error", {"detail": http_exc.detail})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/conversations/{conversation_id}/escalate",
    response_model=EscalationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def escalate_conversation(
    conversation_id: UUID,
    payload: EscalationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> EscalationResponse:
    try:
        escalation, ticket = await service.escalate_conversation(
            db,
            actor=current_user,
            conversation_id=conversation_id,
            reason=payload.reason,
            notes=payload.notes,
        )
    except Exception as exc:
        raise _handle_chat_errors(exc) from exc
    payload_out = EscalationResponse.model_validate(escalation)
    return payload_out.model_copy(
        update={
            "ticket_id": ticket.id if ticket is not None else None,
            "ticket_number": ticket.ticket_number if ticket is not None else None,
        }
    )
