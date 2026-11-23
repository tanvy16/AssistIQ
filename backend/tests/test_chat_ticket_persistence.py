"""Isolated tests for chat → real ticket persistence. No Neon, no Ollama."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.intents import INTENT_ROUTE_MAP, ChatIntent
from app.agents.nodes.create_support_ticket import create_support_ticket
from app.agents.nodes.escalate import escalate
from app.agents.nodes.retrieve_context import retrieve_context
from app.agents.nodes.route_request import route_request
from app.models.enums import UserRole
from app.services.knowledge_base_service import KnowledgeError
from app.services.ticket_service import (
    TicketAccessDeniedError,
    TicketError,
    ensure_ticket_for_conversation,
)


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class _FakeSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    async def execute(self, _stmt):
        return _FakeResult(self.existing)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


def _employee(user_id: uuid.UUID | None = None):
    return SimpleNamespace(id=user_id or uuid.uuid4(), role=UserRole.EMPLOYEE)


def _agent():
    return SimpleNamespace(id=uuid.uuid4(), role=UserRole.AGENT)


@pytest.mark.asyncio
async def test_ensure_reuses_existing_conversation_ticket():
    conv_id = uuid.uuid4()
    requester = uuid.uuid4()
    existing = SimpleNamespace(id=uuid.uuid4(), ticket_number="TICK-00007", conversation_id=conv_id)
    session = _FakeSession(existing=existing)

    ticket = await ensure_ticket_for_conversation(
        session,
        actor=_employee(requester),
        conversation_id=conv_id,
        requester_id=requester,
        title="Help",
        description="VPN still down",
    )

    assert ticket is existing
    assert session.added == []


@pytest.mark.asyncio
async def test_ensure_creates_ticket_when_missing(monkeypatch):
    conv_id = uuid.uuid4()
    requester = uuid.uuid4()
    session = _FakeSession()
    due = datetime.now(UTC)

    monkeypatch.setattr(
        "app.services.ticket_service.calculate_sla_due_at_for_priority",
        AsyncMock(return_value=due),
    )
    monkeypatch.setattr(
        "app.services.ticket_service._next_ticket_number",
        AsyncMock(return_value="TICK-00042"),
    )

    ticket = await ensure_ticket_for_conversation(
        session,
        actor=_employee(requester),
        conversation_id=conv_id,
        requester_id=requester,
        title="VPN issue",
        description="Cannot connect",
    )

    assert ticket.ticket_number == "TICK-00042"
    assert ticket.conversation_id == conv_id
    assert ticket.requester_id == requester
    assert any(obj is ticket for obj in session.added)


@pytest.mark.asyncio
async def test_employee_cannot_create_ticket_for_another_user():
    with pytest.raises(TicketAccessDeniedError):
        await ensure_ticket_for_conversation(
            _FakeSession(),
            actor=_employee(),
            conversation_id=uuid.uuid4(),
            requester_id=uuid.uuid4(),
            title="x",
            description="y",
        )


@pytest.mark.asyncio
async def test_agent_can_create_ticket_on_behalf_of_employee(monkeypatch):
    requester = uuid.uuid4()
    monkeypatch.setattr(
        "app.services.ticket_service.calculate_sla_due_at_for_priority",
        AsyncMock(return_value=datetime.now(UTC)),
    )
    monkeypatch.setattr(
        "app.services.ticket_service._next_ticket_number",
        AsyncMock(return_value="TICK-00099"),
    )

    ticket = await ensure_ticket_for_conversation(
        _FakeSession(),
        actor=_agent(),
        conversation_id=uuid.uuid4(),
        requester_id=requester,
        title="Help",
        description="Need agent",
    )
    assert ticket.requester_id == requester
    assert ticket.ticket_number == "TICK-00099"


@pytest.mark.asyncio
async def test_ensure_fails_honestly_without_sla(monkeypatch):
    from app.services.sla_service import SlaPolicyNotFoundError

    monkeypatch.setattr(
        "app.services.ticket_service.calculate_sla_due_at_for_priority",
        AsyncMock(side_effect=SlaPolicyNotFoundError("missing")),
    )
    requester = uuid.uuid4()
    with pytest.raises(TicketError, match="SLA policy"):
        await ensure_ticket_for_conversation(
            _FakeSession(),
            actor=_employee(requester),
            conversation_id=uuid.uuid4(),
            requester_id=requester,
            title="x",
            description="y",
        )


@pytest.mark.asyncio
async def test_escalate_node_mentions_persisted_ticket(monkeypatch):
    ticket = SimpleNamespace(id=uuid.uuid4(), ticket_number="TICK-00011")
    monkeypatch.setattr(
        "app.agents.nodes.escalate.ensure_ticket_for_conversation",
        AsyncMock(return_value=ticket),
    )
    actor = _employee()
    result = await escalate(
        {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(actor.id),
            "user_message": "Please speak to a human",
        },
        {"configurable": {"db": object(), "actor": actor}},
    )
    assert "TICK-00011" in result["answer"]
    assert result["escalation_triggered"] is True
    assert result["ticket_id"] == str(ticket.id)
    assert result["skip_generation"] is True


@pytest.mark.asyncio
async def test_escalate_node_does_not_claim_success_on_failure(monkeypatch):
    monkeypatch.setattr(
        "app.agents.nodes.escalate.ensure_ticket_for_conversation",
        AsyncMock(side_effect=TicketError("SLA policy is not configured")),
    )
    actor = _employee()
    result = await escalate(
        {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(actor.id),
            "user_message": "escalate please",
        },
        {"configurable": {"db": object(), "actor": actor}},
    )
    assert "TICK-" not in result["answer"]
    assert "could not create" in result["answer"].lower()
    assert result["escalation_triggered"] is False


@pytest.mark.asyncio
async def test_create_support_ticket_node_persists(monkeypatch):
    ticket = SimpleNamespace(id=uuid.uuid4(), ticket_number="TICK-00021")
    monkeypatch.setattr(
        "app.agents.nodes.create_support_ticket.ensure_ticket_for_conversation",
        AsyncMock(return_value=ticket),
    )
    actor = _employee()
    result = await create_support_ticket(
        {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(actor.id),
            "user_message": "Please create a ticket for my VPN issue",
        },
        {"configurable": {"db": object(), "actor": actor}},
    )
    assert "TICK-00021" in result["answer"]
    assert result["escalation_triggered"] is False
    assert result["ticket_number"] == "TICK-00021"


def test_ticket_creation_intent_routes_to_create_support_ticket():
    assert INTENT_ROUTE_MAP[ChatIntent.TICKET_CREATION_REQUEST.value] == "create_support_ticket"
    assert route_request({"intent": ChatIntent.TICKET_CREATION_REQUEST.value}) == "create_support_ticket"
    assert route_request({"intent": ChatIntent.HUMAN_ESCALATION.value}) == "escalate"
    assert route_request({"intent": ChatIntent.TICKET_QUERY.value}) == "retrieve_ticket_context"


@pytest.mark.asyncio
async def test_retrieve_context_returns_empty_when_chroma_fails(monkeypatch):
    class BoomKB:
        async def search_published(self, *_args, **_kwargs):
            raise KnowledgeError("Search failed")

    monkeypatch.setattr("app.agents.nodes.retrieve_context.get_knowledge_service", lambda: BoomKB())
    result = await retrieve_context(
        {"user_message": "how do I connect to VPN", "top_k": 3},
        {"configurable": {"db": object()}},
    )
    assert result["citations"] == []
    assert result["retrieved_count"] == 0
    assert result["top_similarity_score"] is None
