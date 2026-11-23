"""Regressions found during the final submission sprint (isolated DB only)."""

import pytest

from tests.conftest import ticket_payload


@pytest.mark.asyncio
async def test_agent_resolving_unassigned_ticket_claims_it_and_gets_200(
    client, employee_auth, agent_auth, agent_user, sla_policies
):
    created = await client.post("/api/v1/tickets", headers=employee_auth, json=ticket_payload())
    ticket_id = created.json()["id"]

    # Previously: the update committed, then the response re-check returned 403.
    resolved = await client.patch(
        f"/api/v1/tickets/{ticket_id}", headers=agent_auth, json={"status": "resolved"}
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["status"] == "resolved"
    assert body["assignee"]["id"] == str(agent_user.id)

    # The agent can still open the ticket afterwards.
    assert (await client.get(f"/api/v1/tickets/{ticket_id}", headers=agent_auth)).status_code == 200

    events = (await client.get(f"/api/v1/tickets/{ticket_id}/events", headers=agent_auth)).json()
    kinds = [e["event_type"] for e in events]
    assert "ticket.assigned" in kinds and "ticket.status_changed" in kinds
