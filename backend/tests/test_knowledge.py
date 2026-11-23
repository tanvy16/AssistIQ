import uuid

import pytest
from sqlalchemy import delete, select

from app.models.enums import KnowledgeDocumentStatus, TicketCategory, UserRole
from app.models.knowledge import DocumentChunk, KnowledgeDocument


def knowledge_payload(**overrides):
    data = {
        "title": "Corporate Password Reset",
        "description": "Self-service password reset guide",
        "body": (
            "Use the corporate password self-service portal to reset your password. "
            "Verify MFA and choose a strong password that meets corporate policy."
        ),
        "category": "access",
        "source": "internal-runbook",
    }
    data.update(overrides)
    return data


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
async def cleanup_knowledge(db_session):
    yield
    await db_session.execute(delete(DocumentChunk))
    await db_session.execute(delete(KnowledgeDocument))
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_create_list_get_update_publish_archive_delete(
    client,
    db_session,
    admin_auth,
    admin_user,
    chroma_isolated,
    cleanup_knowledge,
):
    create_resp = await client.post(
        "/api/v1/knowledge",
        headers=admin_auth,
        json=knowledge_payload(),
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["status"] == "draft"
    document_id = created["id"]

    list_resp = await client.get("/api/v1/knowledge", headers=admin_auth)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    get_resp = await client.get(f"/api/v1/knowledge/{document_id}", headers=admin_auth)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Corporate Password Reset"

    patch_resp = await client.patch(
        f"/api/v1/knowledge/{document_id}",
        headers=admin_auth,
        json={"title": "Updated Password Reset"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Password Reset"

    publish_resp = await client.post(
        f"/api/v1/knowledge/{document_id}/publish",
        headers=admin_auth,
    )
    assert publish_resp.status_code == 200
    published = publish_resp.json()
    assert published["status"] == "published"

    from sqlalchemy import func

    chunk_count = await db_session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == uuid.UUID(document_id))
    )
    assert chunk_count and chunk_count > 0

    archive_resp = await client.post(
        f"/api/v1/knowledge/{document_id}/archive",
        headers=admin_auth,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"

    delete_resp = await client.delete(
        f"/api/v1/knowledge/{document_id}",
        headers=admin_auth,
    )
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_employee_agent_search_published_only(
    client,
    db_session,
    admin_auth,
    employee_auth,
    agent_auth,
    admin_user,
    chroma_isolated,
    cleanup_knowledge,
):
    draft_resp = await client.post(
        "/api/v1/knowledge",
        headers=admin_auth,
        json=knowledge_payload(
            title="Draft VPN Guide",
            body="Draft-only VPN content should not appear in search.",
            category="network",
        ),
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.json()["id"]

    published_resp = await client.post(
        "/api/v1/knowledge",
        headers=admin_auth,
        json=knowledge_payload(
            title="Published Password Guide",
            body="Published password reset content for employees and agents.",
        ),
    )
    assert published_resp.status_code == 201
    published_id = published_resp.json()["id"]
    assert (
        await client.post(
            f"/api/v1/knowledge/{published_id}/publish",
            headers=admin_auth,
        )
    ).status_code == 200

    for auth in (employee_auth, agent_auth):
        search_resp = await client.post(
            "/api/v1/knowledge/search",
            headers=auth,
            json={"query": "password reset portal", "top_k": 5},
        )
        assert search_resp.status_code == 200
        results = search_resp.json()["results"]
        assert results
        assert all(item["title"] == "Published Password Guide" for item in results)
        assert all(str(draft_id) not in str(item["document_id"]) for item in results)

        draft_get = await client.get(f"/api/v1/knowledge/{draft_id}", headers=auth)
        assert draft_get.status_code == 403


@pytest.mark.asyncio
async def test_rbac_admin_only_mutations(client, employee_auth, agent_auth):
    create_resp = await client.post(
        "/api/v1/knowledge",
        headers=employee_auth,
        json=knowledge_payload(),
    )
    assert create_resp.status_code == 403

    create_resp = await client.post(
        "/api/v1/knowledge",
        headers=agent_auth,
        json=knowledge_payload(),
    )
    assert create_resp.status_code == 403


@pytest.mark.asyncio
async def test_archived_documents_excluded_from_search(
    client,
    admin_auth,
    employee_auth,
    chroma_isolated,
    cleanup_knowledge,
):
    create_resp = await client.post(
        "/api/v1/knowledge",
        headers=admin_auth,
        json=knowledge_payload(
            title="Archived Password Guide",
            body="Archived password reset content should not be searchable.",
        ),
    )
    document_id = create_resp.json()["id"]
    assert (
        await client.post(
            f"/api/v1/knowledge/{document_id}/publish",
            headers=admin_auth,
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/api/v1/knowledge/{document_id}/archive",
            headers=admin_auth,
        )
    ).status_code == 200

    search_resp = await client.post(
        "/api/v1/knowledge/search",
        headers=employee_auth,
        json={"query": "password reset archived", "top_k": 5},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_validation(client, employee_auth, chroma_isolated, cleanup_knowledge):
    empty_resp = await client.post(
        "/api/v1/knowledge/search",
        headers=employee_auth,
        json={"query": "   ", "top_k": 5},
    )
    assert empty_resp.status_code == 422 or empty_resp.status_code == 400

    topk_resp = await client.post(
        "/api/v1/knowledge/search",
        headers=employee_auth,
        json={"query": "password", "top_k": 999},
    )
    assert topk_resp.status_code in (400, 422)
