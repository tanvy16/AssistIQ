"""Chat conversation orchestration service."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.graphs.chat_graph import build_chat_graph
from app.ai.enums import AIModelType, AITaskType
from app.core.config import Settings, get_settings
from app.models.chat import (
    ChatInteractionTelemetry,
    ChatMessage,
    ChatMessageRole,
    ConfidenceState,
    Conversation,
    ConversationStatus,
    Escalation,
    EscalationStatus,
    MessageCitation,
)
from app.models.enums import UserRole
from app.models.user import User
from app.services.ai_model_service import (
    AIModelDisabledError,
    AIModelNotFoundError,
    AIModelService,
    AIModelValidationError,
    get_ai_model_service,
)
from app.services.audit_service import record_audit_event
from app.services.ticket_service import TicketError, ensure_ticket_for_conversation


class ChatError(Exception):
    pass


class ChatNotFoundError(ChatError):
    pass


class ChatAccessDeniedError(ChatError):
    pass


class ChatValidationError(ChatError):
    pass


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        ai_service: AIModelService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ai = ai_service or get_ai_model_service()

    async def create_conversation(
        self,
        db: AsyncSession,
        *,
        actor: User,
        title: str | None = None,
        selected_model_id: uuid.UUID | None = None,
    ) -> Conversation:
        generation_model_id = await self._resolve_generation_model_id(db, selected_model_id)
        conversation = Conversation(
            user_id=actor.id,
            title=(title or "New conversation").strip()[:200],
            status=ConversationStatus.ACTIVE,
            selected_model_id=generation_model_id,
        )
        db.add(conversation)
        await db.flush()
        await record_audit_event(
            db,
            event_type="chat.conversation.created",
            user_id=actor.id,
            payload={"conversation_id": str(conversation.id)},
        )
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def list_conversations(
        self,
        db: AsyncSession,
        *,
        actor: User,
    ) -> list[Conversation]:
        query = select(Conversation).order_by(Conversation.updated_at.desc())
        if actor.role == UserRole.EMPLOYEE:
            query = query.where(Conversation.user_id == actor.id)
        elif actor.role == UserRole.AGENT:
            query = query  # agents see all for support oversight
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_conversation(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self._get_conversation_or_404(db, conversation_id)
        self._ensure_access(actor, conversation)
        return conversation

    async def list_messages(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation_id: uuid.UUID,
    ) -> list[ChatMessage]:
        conversation = await self.get_conversation(db, actor=actor, conversation_id=conversation_id)
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .options(selectinload(ChatMessage.citations))
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def send_message(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation_id: uuid.UUID,
        content: str,
        selected_model_id: uuid.UUID | None = None,
    ) -> tuple[ChatMessage, ChatMessage]:
        started = time.perf_counter()
        conversation = await self.get_conversation(db, actor=actor, conversation_id=conversation_id)
        self._ensure_owner(actor, conversation)
        clean_content = content.strip()
        if not clean_content:
            raise ChatValidationError("Message content must not be empty")

        generation_model_id = await self._resolve_generation_model_id(
            db, selected_model_id or conversation.selected_model_id
        )
        intent_model_id = await self._resolve_intent_model_id(db)
        conversation.selected_model_id = generation_model_id

        user_message = ChatMessage(
            conversation_id=conversation.id,
            role=ChatMessageRole.USER,
            content=clean_content,
        )
        db.add(user_message)
        await db.flush()

        history = await self._load_history(db, conversation.id)
        graph_state = await self._invoke_graph(
            db,
            actor=actor,
            conversation=conversation,
            clean_content=clean_content,
            history=history,
            generation_model_id=generation_model_id,
            intent_model_id=intent_model_id,
            defer_generation=False,
        )
        return await self._persist_turn(
            db,
            actor=actor,
            conversation=conversation,
            user_message=user_message,
            generation_model_id=generation_model_id,
            graph_state=graph_state,
            started=started,
        )

    async def send_message_stream(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation_id: uuid.UUID,
        content: str,
        selected_model_id: uuid.UUID | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        started = time.perf_counter()
        conversation = await self.get_conversation(db, actor=actor, conversation_id=conversation_id)
        self._ensure_owner(actor, conversation)
        clean_content = content.strip()
        if not clean_content:
            raise ChatValidationError("Message content must not be empty")

        generation_model_id = await self._resolve_generation_model_id(
            db, selected_model_id or conversation.selected_model_id
        )
        intent_model_id = await self._resolve_intent_model_id(db)
        conversation.selected_model_id = generation_model_id

        user_message = ChatMessage(
            conversation_id=conversation.id,
            role=ChatMessageRole.USER,
            content=clean_content,
        )
        db.add(user_message)
        await db.flush()

        history = await self._load_history(db, conversation.id)
        graph_state = await self._invoke_graph(
            db,
            actor=actor,
            conversation=conversation,
            clean_content=clean_content,
            history=history,
            generation_model_id=generation_model_id,
            intent_model_id=intent_model_id,
            defer_generation=True,
        )

        prompt = graph_state.get("generation_prompt")
        yield {
            "event": "meta",
            "data": {
                "conversation_id": str(conversation.id),
                "intent": graph_state.get("intent"),
                "confidence_state": graph_state.get("confidence_state"),
                "citations": self._citation_previews(graph_state.get("citations") or []),
            },
        }

        if prompt:
            pieces: list[str] = []
            gen_started = time.perf_counter()
            try:
                async for delta in self._ai.stream_text(
                    db,
                    actor=actor,
                    model_id=generation_model_id,
                    task=AITaskType.GENERATION,
                    input_data={
                        "text": prompt,
                        "instruction": "Answer the IT support question using retrieved DATA only.",
                    },
                    metadata={
                        "conversation_id": str(conversation.id),
                        "intent": graph_state.get("intent"),
                    },
                ):
                    pieces.append(delta)
                    yield {"event": "token", "data": {"text": delta}}
            except (AIModelValidationError, AIModelDisabledError, AIModelNotFoundError) as exc:
                if not pieces:
                    raise ChatValidationError(str(exc)) from exc
            graph_state = {
                **graph_state,
                "answer": "".join(pieces).strip(),
                "generation_latency_ms": (time.perf_counter() - gen_started) * 1000,
            }

        user_message, assistant_message = await self._persist_turn(
            db,
            actor=actor,
            conversation=conversation,
            user_message=user_message,
            generation_model_id=generation_model_id,
            graph_state=graph_state,
            started=started,
        )
        yield {
            "event": "done",
            "data": {
                "user_message": user_message,
                "assistant_message": assistant_message,
            },
        }

    async def _invoke_graph(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation: Conversation,
        clean_content: str,
        history: list[dict[str, str]],
        generation_model_id: uuid.UUID,
        intent_model_id: uuid.UUID | None,
        defer_generation: bool,
    ) -> dict[str, Any]:
        graph = build_chat_graph()
        return await graph.ainvoke(
            {
                "conversation_id": str(conversation.id),
                "user_id": str(actor.id),
                "user_message": clean_content,
                "history": history,
                "selected_model_id": str(generation_model_id),
                "generation_model_id": str(generation_model_id),
                "intent_model_id": str(intent_model_id) if intent_model_id else None,
                "top_k": self._settings.CHAT_RETRIEVAL_TOP_K,
            },
            config={
                "configurable": {
                    "db": db,
                    "actor": actor,
                    "defer_generation": defer_generation,
                }
            },
        )

    async def _persist_turn(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation: Conversation,
        user_message: ChatMessage,
        generation_model_id: uuid.UUID,
        graph_state: dict[str, Any],
        started: float,
    ) -> tuple[ChatMessage, ChatMessage]:
        usage = graph_state.get("generation_usage") or {}
        confidence_raw = graph_state.get("confidence_state")
        confidence = ConfidenceState(confidence_raw) if confidence_raw else None

        assistant_message = ChatMessage(
            conversation_id=conversation.id,
            role=ChatMessageRole.ASSISTANT,
            content=graph_state.get("answer") or "",
            model_id=generation_model_id,
            latency_ms=graph_state.get("generation_latency_ms"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            intent=graph_state.get("intent"),
            confidence_state=confidence,
            message_metadata={
                "route": graph_state.get("route"),
                "retrieved_count": graph_state.get("retrieved_count"),
                "ticket_id": graph_state.get("ticket_id"),
                "ticket_number": graph_state.get("ticket_number"),
            },
        )
        db.add(assistant_message)
        await db.flush()

        for citation in graph_state.get("citations") or []:
            db.add(
                MessageCitation(
                    message_id=assistant_message.id,
                    document_id=uuid.UUID(citation["document_id"]),
                    chunk_id=uuid.UUID(citation["chunk_id"]),
                    title=citation["title"],
                    similarity_score=float(citation["similarity_score"]),
                    citation_metadata={
                        "content_excerpt": (citation.get("content") or "")[:200],
                        "category": citation.get("category"),
                    },
                )
            )

        if graph_state.get("escalation_triggered"):
            await self._create_escalation_record(
                db,
                conversation=conversation,
                actor=actor,
                reason=graph_state.get("escalation_reason") or "low_confidence",
            )

        total_latency = (time.perf_counter() - started) * 1000
        db.add(
            ChatInteractionTelemetry(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                user_id=actor.id,
                intent=graph_state.get("intent"),
                retrieval_latency_ms=graph_state.get("retrieval_latency_ms"),
                generation_latency_ms=graph_state.get("generation_latency_ms"),
                total_latency_ms=total_latency,
                top_k=graph_state.get("top_k"),
                retrieved_count=graph_state.get("retrieved_count"),
                top_similarity_score=graph_state.get("top_similarity_score"),
                citation_count=len(graph_state.get("citations") or []),
                confidence_state=confidence_raw,
                escalation_triggered=bool(graph_state.get("escalation_triggered")),
            )
        )

        if conversation.title == "New conversation":
            conversation.title = (user_message.content or "")[:80]

        await record_audit_event(
            db,
            event_type="chat.message.sent",
            user_id=actor.id,
            payload={
                "conversation_id": str(conversation.id),
                "intent": graph_state.get("intent"),
            },
        )
        await db.commit()
        await db.refresh(user_message)
        await db.refresh(assistant_message)
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.id == assistant_message.id)
            .options(selectinload(ChatMessage.citations))
        )
        assistant_with_citations = result.scalar_one()
        return user_message, assistant_with_citations

    def _citation_previews(self, citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        previews: list[dict[str, Any]] = []
        for citation in citations:
            previews.append(
                {
                    "id": citation.get("chunk_id"),
                    "document_id": citation.get("document_id"),
                    "chunk_id": citation.get("chunk_id"),
                    "title": citation.get("title"),
                    "similarity_score": citation.get("similarity_score"),
                    "category": citation.get("category"),
                }
            )
        return previews

    async def escalate_conversation(
        self,
        db: AsyncSession,
        *,
        actor: User,
        conversation_id: uuid.UUID,
        reason: str,
        notes: str | None = None,
    ) -> tuple[Escalation, Any]:
        conversation = await self.get_conversation(db, actor=actor, conversation_id=conversation_id)
        description = notes or (
            f"Escalated from chat conversation {conversation.id}. Reason: {reason}."
        )
        try:
            ticket = await ensure_ticket_for_conversation(
                db,
                actor=actor,
                conversation_id=conversation.id,
                requester_id=conversation.user_id,
                title=(notes or reason)[:200],
                description=description,
            )
        except TicketError as exc:
            raise ChatValidationError(str(exc)) from exc

        escalation = await self._create_escalation_record(
            db,
            conversation=conversation,
            actor=actor,
            reason=reason,
            notes=notes,
        )
        await record_audit_event(
            db,
            event_type="chat.escalation.requested",
            user_id=actor.id,
            payload={
                "conversation_id": str(conversation.id),
                "reason": reason,
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
            },
        )
        await db.commit()
        await db.refresh(escalation)
        return escalation, ticket

    async def _resolve_generation_model_id(
        self,
        db: AsyncSession,
        model_id: uuid.UUID | None,
    ) -> uuid.UUID:
        try:
            if model_id is not None:
                model = await self._ai.get_model(db, model_id)
                if model.model_type != AIModelType.LLM:
                    raise ChatValidationError(
                        "Chat generation requires an enabled LLM model. "
                        "Lightweight ML and Deep Learning models support classification tasks only."
                    )
                if AITaskType.GENERATION.value not in (model.capabilities or []):
                    raise ChatValidationError("Selected model does not support generation")
                return model.id

            models = await self._ai.list_models(db)
            llms = [
                model
                for model in models
                if model.model_type == AIModelType.LLM
                and AITaskType.GENERATION.value in (model.capabilities or [])
            ]
            preferred = self._settings.LLM_PROVIDER.lower()
            for model in llms:
                if (model.provider or "").lower() == preferred:
                    return model.id
            if llms:
                return llms[0].id
            raise ChatValidationError("No enabled LLM model available for chat generation")
        except (AIModelNotFoundError, AIModelDisabledError, AIModelValidationError) as exc:
            raise ChatValidationError(str(exc)) from exc

    async def _resolve_intent_model_id(self, db: AsyncSession) -> uuid.UUID | None:
        models = await self._ai.list_models(db)
        for model in models:
            if model.model_type == AIModelType.LIGHTWEIGHT_ML and AITaskType.INTENT_DETECTION.value in (
                model.capabilities or []
            ):
                return model.id
        return None

    async def _load_history(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> list[dict[str, str]]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(self._settings.CHAT_HISTORY_LIMIT + 1)
        )
        rows = list(reversed(result.scalars().all()))
        if rows and rows[-1].role == ChatMessageRole.USER:
            rows = rows[:-1]
        rows = rows[-self._settings.CHAT_HISTORY_LIMIT :]
        return [{"role": row.role.value, "content": row.content} for row in rows]

    async def _get_conversation_or_404(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ChatNotFoundError("Conversation not found")
        return conversation

    def _ensure_access(self, actor: User, conversation: Conversation) -> None:
        if actor.role == UserRole.EMPLOYEE and conversation.user_id != actor.id:
            raise ChatAccessDeniedError("You do not have access to this conversation")
        if actor.role not in {UserRole.EMPLOYEE, UserRole.AGENT, UserRole.ADMIN}:
            raise ChatAccessDeniedError("Insufficient permissions")

    def _ensure_owner(self, actor: User, conversation: Conversation) -> None:
        # Agents/admins may READ conversations for support oversight, but only the
        # owner may post. Otherwise a privileged user could drive chat actions
        # (IT requests, password resets) inside someone else's conversation.
        if conversation.user_id != actor.id:
            raise ChatAccessDeniedError("Only the conversation owner can send messages")

    async def _create_escalation_record(
        self,
        db: AsyncSession,
        *,
        conversation: Conversation,
        actor: User,
        reason: str,
        notes: str | None = None,
    ) -> Escalation:
        conversation.status = ConversationStatus.ESCALATED
        escalation = Escalation(
            conversation_id=conversation.id,
            requested_by=actor.id,
            reason=reason[:128],
            status=EscalationStatus.OPEN,
            notes=notes,
        )
        db.add(escalation)
        await db.flush()
        return escalation


_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def reset_chat_service() -> None:
    global _chat_service
    _chat_service = None
