import pytest

from tests.conftest import ticket_payload


@pytest.mark.asyncio
async def test_agent_dashboard_queue_and_assigned_counts(
    client,
    sla_policies,
    employee_auth,
    agent_auth,
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(title="Unassigned queue ticket"),
        headers=employee_auth,
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    stats = await client.get("/api/v1/tickets/stats", headers=agent_auth)
    assert stats.status_code == 200
    body = stats.json()
    queue_list = await client.get("/api/v1/tickets?scope=queue&page_size=100", headers=agent_auth)
    assert queue_list.status_code == 200
    queue_ids = {item["id"] for item in queue_list.json()["items"]}
    assert ticket_id in queue_ids
    assert body["unassigned_queue"] == queue_list.json()["total"]
    assert body["open"] >= 1

    summary = await client.get("/api/v1/dashboard/summary", headers=agent_auth)
    assert summary.status_code == 200
    dashboard = summary.json()
    assert dashboard["tickets"]["unassigned_queue"] == body["unassigned_queue"]
    assert dashboard["health"]["api"] == "ok"
    assert dashboard["knowledge"] is None

    claimed = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={},
        headers=agent_auth,
    )
    assert claimed.status_code == 200

    after = await client.get("/api/v1/tickets/stats", headers=agent_auth)
    assert after.status_code == 200
    after_body = after.json()
    assert after_body["assigned_to_me"] >= 1

    queue = await client.get("/api/v1/tickets?scope=queue&page_size=100", headers=agent_auth)
    assigned = await client.get("/api/v1/tickets?scope=assigned&page_size=100", headers=agent_auth)
    queue_ids = {item["id"] for item in queue.json()["items"]}
    assigned_ids = {item["id"] for item in assigned.json()["items"]}
    assert ticket_id not in queue_ids
    assert ticket_id in assigned_ids
    assert after_body["unassigned_queue"] == queue.json()["total"]

    refreshed = await client.get("/api/v1/dashboard/summary", headers=agent_auth)
    activity_types = {item["event_type"] for item in refreshed.json()["recent_activity"]}
    assert "ticket.assigned" in activity_types or "ticket.status_changed" in activity_types


@pytest.mark.asyncio
async def test_admin_dashboard_includes_operational_counts(
    client,
    sla_policies,
    admin_auth,
    employee_auth,
):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(title="Admin dashboard ticket"),
        headers=employee_auth,
    )
    assert created.status_code == 201

    summary = await client.get("/api/v1/dashboard/summary", headers=admin_auth)
    assert summary.status_code == 200
    body = summary.json()
    assert body["tickets"]["total"] >= 1
    assert body["users"]["total"] >= 1
    assert body["users"]["active_agents"] >= 0
    assert body["knowledge"]["total"] >= 0
    assert "request_count" in body["ai"]
    assert body["health"]["database"] in {"connected", "unavailable"}

    users = await client.get("/api/v1/users", headers=admin_auth)
    assert users.status_code == 200
    assert users.json()["total"] >= 1
    assert "password_hash" not in users.json()["items"][0]


@pytest.mark.asyncio
async def test_employee_cannot_list_users(client, employee_auth):
    response = await client.get("/api/v1/users", headers=employee_auth)
    assert response.status_code == 403
