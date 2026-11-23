import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, select

from app.agents.intents import ChatIntent
from app.agents.nodes.detect_intent import detect_intent
from app.models.chat import (
    ChatInteractionTelemetry,
    ChatMessage,
    Conversation,
    Escalation,
    MessageCitation,
)
from app.models.ticket import Ticket, TicketComment, TicketEvent
from tests.ai_fixtures import model_by_key


@pytest.fixture
async def chroma_isolated(tmp_path, monkeypatch):
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    from app.adapters.chroma import reset_chroma_adapter
    from app.core.config import get_settings
    from app.services.embedding_service import reset_embedding_service
    from app.services.knowledge_base_service import reset_knowledge_service

    get_settings.cache_clear()
    reset_chroma_adapter()
    reset_embedding_service()
    reset_knowledge_service()
    yield chroma_path
    reset_chroma_adapter()
    reset_embedding_service()
    reset_knowledge_service()
    get_settings.cache_clear()


@pytest.fixture
async def cleanup_knowledge():
    from app.models.knowledge import DocumentChunk, KnowledgeDocument

    yield
    from app.core.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(DocumentChunk))
        await session.execute(delete(KnowledgeDocument))
        await session.commit()


@pytest.fixture
async def cleanup_chat():
    yield
    from app.core.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        chat_ticket_ids = select(Ticket.id).where(Ticket.conversation_id.is_not(None))
        await session.execute(delete(TicketComment).where(TicketComment.ticket_id.in_(chat_ticket_ids)))
        await session.execute(delete(TicketEvent).where(TicketEvent.ticket_id.in_(chat_ticket_ids)))
        await session.execute(delete(Ticket).where(Ticket.conversation_id.is_not(None)))
        await session.execute(delete(MessageCitation))
        await session.execute(delete(ChatInteractionTelemetry))
        await session.execute(delete(Escalation))
        await session.execute(delete(ChatMessage))
        await session.execute(delete(Conversation))
        await session.commit()


def _llm_mock_result():
    return {
        "request_id": str(uuid.uuid4()),
        "output": {"text": "Use the VPN troubleshooting guide to reconnect.", "finish_reason": "stop"},
        "model_type": "llm",
        "model_id": str(uuid.uuid4()),
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "latency_ms": 120.0,
        "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70, "estimated_cost_usd": 0.001},
    }


@pytest.mark.asyncio
async def test_create_conversation(client, employee_auth, ai_models, cleanup_chat):
    llm = model_by_key(ai_models, "test-llm-v1")
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"title": "VPN help", "selected_model_id": str(llm.id)},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "VPN help"
    assert body["selected_model_id"] == str(llm.id)


@pytest.mark.asyncio
async def test_employee_cannot_access_other_conversation(
    client, employee_auth, employee_b_auth, ai_models, cleanup_chat
):
    llm = model_by_key(ai_models, "test-llm-v1")
    create_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = create_resp.json()["id"]
    get_resp = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}",
        headers=employee_b_auth,
    )
    assert get_resp.status_code == 403


@pytest.mark.asyncio
async def test_send_message_with_mocked_llm(
    client,
    db_session,
    employee_auth,
    ai_models,
    cleanup_chat,
):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]

    with patch(
        "app.agents.nodes.generate_answer.get_ai_model_service"
    ) as mock_service_factory:
        mock_service = AsyncMock()
        mock_service.infer = AsyncMock(return_value=_llm_mock_result())
        mock_service_factory.return_value = mock_service
        msg_resp = await client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=employee_auth,
            json={"content": "How do I fix VPN connection issues?"},
        )

    assert msg_resp.status_code == 200
    body = msg_resp.json()
    assert body["assistant_message"]["content"]
    assert body["assistant_message"]["total_tokens"] == 70

    telemetry = await db_session.scalar(select(ChatInteractionTelemetry))
    assert telemetry is not None
    assert telemetry.intent is not None


@pytest.mark.asyncio
async def test_password_reset_intent_does_not_execute_workflow(
    client, employee_auth, ai_models, cleanup_chat
):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]

    msg_resp = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=employee_auth,
        json={"content": "Please reset my password now"},
    )

    assert msg_resp.status_code == 200
    answer = msg_resp.json()["assistant_message"]["content"].lower()
    assert "verification" in answer or "secure" in answer
    assert "reset complete" not in answer
    assert "has been changed" not in answer


@pytest.mark.asyncio
async def test_unsupported_generation_model_rejected(
    client, employee_auth, ai_models, cleanup_chat
):
    ml = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(ml.id)},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_escalate_conversation(client, employee_auth, ai_models, sla_policies, cleanup_chat):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]
    esc_resp = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/escalate",
        headers=employee_auth,
        json={"reason": "user_requested_human"},
    )
    assert esc_resp.status_code == 201
    body = esc_resp.json()
    assert body["status"] == "open"
    assert body.get("ticket_number")
    assert str(body["ticket_number"]).startswith("TICK-")


@pytest.mark.asyncio
async def test_detect_intent_password_reset():
    state = {"user_message": "I need a password reset for my account"}
    result = await detect_intent(state, {"configurable": {}})
    assert result["intent"] == ChatIntent.PASSWORD_RESET_REQUEST.value


@pytest.mark.asyncio
async def test_detect_intent_human_escalation():
    state = {"user_message": "I want to speak to a human agent please"}
    result = await detect_intent(state, {"configurable": {}})
    assert result["intent"] == ChatIntent.HUMAN_ESCALATION.value


@pytest.mark.asyncio
async def test_list_messages(client, employee_auth, ai_models, cleanup_chat):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]

    with patch(
        "app.agents.nodes.generate_answer.get_ai_model_service"
    ) as mock_service_factory:
        mock_service = AsyncMock()
        mock_service.infer = AsyncMock(return_value=_llm_mock_result())
        mock_service_factory.return_value = mock_service
        await client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=employee_auth,
            json={"content": "Hello"},
        )

    list_resp = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=employee_auth,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


@pytest.mark.asyncio
async def test_llm_null_tokens_when_usage_missing(client, employee_auth, ai_models, cleanup_chat):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]
    mock = _llm_mock_result()
    mock["usage"] = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "estimated_cost_usd": None,
    }

    with patch(
        "app.agents.nodes.generate_answer.get_ai_model_service"
    ) as mock_service_factory:
        mock_service = AsyncMock()
        mock_service.infer = AsyncMock(return_value=mock)
        mock_service_factory.return_value = mock_service
        msg_resp = await client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=employee_auth,
            json={"content": "General IT question"},
        )

    assert msg_resp.status_code == 200
    assert msg_resp.json()["assistant_message"]["total_tokens"] is None


@pytest.mark.asyncio
async def test_send_message_stream_emits_tokens(
    client,
    employee_auth,
    ai_models,
    cleanup_chat,
):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv_resp.json()["id"]

    async def fake_stream(self, *args, **kwargs):
        yield "Connect "
        yield "to the VPN."

    with patch(
        "app.services.ai_model_service.AIModelService.stream_text",
        fake_stream,
    ):
        response = await client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages/stream",
            headers=employee_auth,
            json={"content": "How do I connect to the corporate VPN?"},
        )

    assert response.status_code == 200
    text = response.text
    assert "event: meta" in text
    assert "event: token" in text
    assert "Connect " in text
    assert "event: done" in text
    assert "event: error" not in text


@pytest.mark.asyncio
async def test_unknown_selected_model_returns_400(client, employee_auth, ai_models, cleanup_chat):
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"title": "Stale model", "selected_model_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()
