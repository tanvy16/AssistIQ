import pytest
from sqlalchemy import select

from app.models.enums import TicketEventType, TicketStatus
from app.models.ticket import TicketEvent
from tests.conftest import ticket_payload


@pytest.mark.asyncio
async def test_employee_can_create_ticket(
    client, sla_policies, employee_auth, employee_user
):
    response = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["ticket_number"].startswith("TICK-")
    assert payload["status"] == "open"
    assert payload["requester"]["id"] == str(employee_user.id)
    assert payload["sla_due_at"] is not None


@pytest.mark.asyncio
async def test_employee_sees_only_own_tickets(
    client,
    sla_policies,
    employee_auth,
    employee_b_auth,
):
    create_a = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(title="Employee A ticket"),
        headers=employee_auth,
    )
    create_b = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(title="Employee B ticket"),
        headers=employee_b_auth,
    )
    assert create_a.status_code == 201
    assert create_b.status_code == 201

    list_a = await client.get("/api/v1/tickets", headers=employee_auth)
    assert list_a.status_code == 200
    titles = [item["title"] for item in list_a.json()["items"]]
    assert "Employee A ticket" in titles
    assert "Employee B ticket" not in titles


@pytest.mark.asyncio
async def test_employee_cannot_access_other_ticket(
    client, sla_policies, employee_auth, employee_b_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_b_auth,
    )
    ticket_id = created.json()["id"]
    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=employee_auth,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ticket_creation_records_event(
    client, sla_policies, employee_auth, db_session
):
    response = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = response.json()["id"]
    events = await client.get(
        f"/api/v1/tickets/{ticket_id}/events",
        headers=employee_auth,
    )
    assert events.status_code == 200
    assert any(e["event_type"] == TicketEventType.CREATED.value for e in events.json())


@pytest.mark.asyncio
async def test_agent_can_view_queue_ticket(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]

    detail = await client.get(f"/api/v1/tickets/{ticket_id}", headers=agent_auth)
    assert detail.status_code == 200

    queue = await client.get("/api/v1/tickets?scope=queue", headers=agent_auth)
    assert queue.status_code == 200
    assert any(item["id"] == ticket_id for item in queue.json()["items"])


@pytest.mark.asyncio
async def test_agent_claim_creates_assigned_event(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]

    assign = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={},
        headers=agent_auth,
    )
    assert assign.status_code == 200
    assert assign.json()["status"] == "in_progress"
    assert assign.json()["assignee"] is not None

    events = await client.get(
        f"/api/v1/tickets/{ticket_id}/events",
        headers=agent_auth,
    )
    assert any(
        e["event_type"] == TicketEventType.ASSIGNED.value for e in events.json()
    )


@pytest.mark.asyncio
async def test_admin_can_view_all_tickets(
    client, sla_policies, employee_auth, admin_auth
):
    await client.post("/api/v1/tickets", json=ticket_payload(), headers=employee_auth)
    response = await client.get("/api/v1/tickets", headers=admin_auth)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_status_change_creates_event(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/assign", json={}, headers=agent_auth)

    patch = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "pending"},
        headers=agent_auth,
    )
    assert patch.status_code == 200

    events = await client.get(
        f"/api/v1/tickets/{ticket_id}/events",
        headers=agent_auth,
    )
    assert any(
        e["event_type"] == TicketEventType.STATUS_CHANGED.value for e in events.json()
    )


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/assign", json={}, headers=agent_auth)

    patch = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "closed"},
        headers=agent_auth,
    )
    assert patch.status_code == 400


@pytest.mark.asyncio
async def test_closed_ticket_cannot_change_status(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/assign", json={}, headers=agent_auth)
    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=agent_auth,
    )
    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "closed"},
        headers=agent_auth,
    )

    patch = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers=agent_auth,
    )
    assert patch.status_code == 409


@pytest.mark.asyncio
async def test_comment_creation_works(
    client, sla_policies, employee_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]

    comment = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"body": "Still unable to connect after reboot."},
        headers=employee_auth,
    )
    assert comment.status_code == 201
    assert comment.json()["body"].startswith("Still unable")


@pytest.mark.asyncio
async def test_employee_cannot_update_status(
    client, sla_policies, employee_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]

    patch = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers=employee_auth,
    )
    assert patch.status_code == 403


@pytest.mark.asyncio
async def test_ticket_list_filter_by_status(
    client, sla_policies, employee_auth, agent_auth
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    ticket_id = created.json()["id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/assign", json={}, headers=agent_auth)

    open_only = await client.get(
        "/api/v1/tickets?status=open",
        headers=employee_auth,
    )
    in_progress = await client.get(
        "/api/v1/tickets?status=in_progress",
        headers=employee_auth,
    )
    assert all(item["status"] == "open" for item in open_only.json()["items"])
    assert any(item["id"] == ticket_id for item in in_progress.json()["items"])


@pytest.mark.asyncio
async def test_ticket_number_format(
    client, sla_policies, employee_auth
):
    response = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(),
        headers=employee_auth,
    )
    number = response.json()["ticket_number"]
    assert number.startswith("TICK-")
    assert len(number) == 10
