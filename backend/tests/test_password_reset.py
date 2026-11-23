import pytest
from sqlalchemy import select

from app.iam.adapter import IAMAdapterError, MockIAMAdapter
from app.models.enums import UserRole
from app.models.password_reset import (
    PasswordPolicyDecision,
    PasswordRiskLevel,
    PasswordVerificationStatus,
)
from app.models.user import User
from app.services.password_reset_policy import PasswordPolicyInput, evaluate_password_reset_policy
from app.services.password_risk import RiskInput, assess_password_reset_risk
from app.services.password_verification import VerificationInput, verify_identity
from tests.ai_fixtures import model_by_key

SECRET_TOKENS = ("password", "token", "secret", "credential", "authorization")


def _assert_no_secrets(payload) -> None:
    text = str(payload).lower()
    for token in ("plaintext", "bcrypt", "$2b$"):
        assert token not in text
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert str(key).lower() not in {"password", "token", "secret", "credential"}
            _assert_no_secrets(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_secrets(item)


@pytest.mark.asyncio
async def test_employee_can_create_own_reset(client, employee_auth, employee_user):
    resp = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "verification_required"
    assert body["requester_id"] == str(employee_user.id)
    assert body["target_user_id"] == str(employee_user.id)
    _assert_no_secrets(body)


@pytest.mark.asyncio
async def test_employee_cannot_reset_another_user(
    client, employee_auth, employee_user_b
):
    resp = await client.post(
        "/api/v1/password-resets",
        headers=employee_auth,
        json={"target_user_id": str(employee_user_b.id)},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_access_other_reset(
    client, employee_auth, employee_b_auth
):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    resp = await client.get(f"/api/v1/password-resets/{request_id}", headers=employee_b_auth)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_failed_verification_blocks_execution(client, employee_auth, employee_user):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    verify = await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": "not-the-owner@example.com"},
    )
    assert verify.status_code == 200
    assert verify.json()["verification_status"] == "failed"
    assert verify.json()["status"] == "verification_failed"
    confirm = await client.post(
        f"/api/v1/password-resets/{request_id}/confirm",
        headers=employee_auth,
        json={},
    )
    assert confirm.status_code == 400


@pytest.mark.asyncio
async def test_successful_verification_then_confirm_simulates(
    client, employee_auth, employee_user, db_session
):
    original_hash = employee_user.password_hash
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    verify = await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "confirmation_required"
    confirm = await client.post(
        f"/api/v1/password-resets/{request_id}/confirm",
        headers=employee_auth,
        json={},
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["status"] == "completed"
    assert body["execution_result"]["simulated"] is True
    assert "simulation" in body["execution_result"]["message"].lower()
    assert "has been changed" not in body["execution_result"]["message"].lower()
    _assert_no_secrets(body)
    refreshed = await db_session.get(User, employee_user.id)
    await db_session.refresh(refreshed)
    assert refreshed.password_hash == original_hash


@pytest.mark.asyncio
async def test_duplicate_confirmation_rejected(client, employee_auth, employee_user):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    first = await client.post(f"/api/v1/password-resets/{request_id}/confirm", headers=employee_auth, json={})
    assert first.status_code == 200
    second = await client.post(f"/api/v1/password-resets/{request_id}/confirm", headers=employee_auth, json={})
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_confirmation_required_before_execution(client, employee_auth, employee_user):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    confirm = await client.post(f"/api/v1/password-resets/{request_id}/confirm", headers=employee_auth, json={})
    assert confirm.status_code == 400


@pytest.mark.asyncio
async def test_privileged_admin_reset_escalates(client, admin_auth, admin_user):
    created = await client.post("/api/v1/password-resets", headers=admin_auth, json={})
    request_id = created.json()["id"]
    verify = await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=admin_auth,
        json={"email": admin_user.email},
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "escalated"
    assert verify.json()["risk_level"] in {"high", "critical"}
    confirm = await client.post(f"/api/v1/password-resets/{request_id}/confirm", headers=admin_auth, json={})
    assert confirm.status_code == 400


@pytest.mark.asyncio
async def test_validation_failure_does_not_claim_success(client, employee_auth, employee_user):
    from app.iam.adapter import MockIAMAdapter, set_iam_adapter

    class FailingMockIAMAdapter(MockIAMAdapter):
        async def reset_password(self, *, target_user_id, request_id, context):
            return await super().reset_password(
                target_user_id=target_user_id,
                request_id=request_id,
                context={"force_failure": True},
            )

    set_iam_adapter(FailingMockIAMAdapter())
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    confirm = await client.post(
        f"/api/v1/password-resets/{request_id}/confirm",
        headers=employee_auth,
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["status"] == "escalated"
    assert body["validation_result"]["passed"] is False


@pytest.mark.asyncio
async def test_escalate_creates_record(client, employee_auth):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    resp = await client.post(
        f"/api/v1/password-resets/{request_id}/escalate",
        headers=employee_auth,
        json={"reason": "I need a human"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "escalated"
    types = [event["event_type"] for event in resp.json()["events"]]
    assert "password_reset.escalated" in types


@pytest.mark.asyncio
async def test_chat_password_reset_routes_to_phase8(
    client, employee_auth, ai_models, employee_user
):
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
    assert "verification" in content
    assert "has been changed" not in content
    listed = await client.get("/api/v1/password-resets", headers=employee_auth)
    assert listed.json()["total"] >= 1
    request = listed.json()["items"][0]
    assert request["status"] == "verification_required"
    detail = await client.get(f"/api/v1/password-resets/{request['id']}", headers=employee_auth)
    assert detail.json().get("execution_result") is None


@pytest.mark.asyncio
async def test_audit_events_have_no_secrets(client, employee_auth, employee_user, db_session):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    from app.models.audit_event import AuditEvent

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.event_type.like("password_reset.%"))
    )
    for event in result.scalars().all():
        _assert_no_secrets(event.payload)


@pytest.mark.asyncio
async def test_mock_iam_rejects_arbitrary_commands():
    adapter = MockIAMAdapter()
    from uuid import uuid4

    with pytest.raises(IAMAdapterError):
        await adapter.reset_password(
            target_user_id=uuid4(),
            request_id=uuid4(),
            context={"execution_params": {"powershell": "Set-ADAccountPassword"}},
        )


def test_policy_employee_other_user_denied():
    from uuid import uuid4

    requester = uuid4()
    result = evaluate_password_reset_policy(
        PasswordPolicyInput(
            requester_id=requester,
            target_user_id=uuid4(),
            requester_role=UserRole.EMPLOYEE,
            verification_status=PasswordVerificationStatus.VERIFIED,
            risk_level=PasswordRiskLevel.LOW,
        )
    )
    assert result.decision == PasswordPolicyDecision.DENY


def test_policy_low_risk_requires_confirmation_not_allow():
    from uuid import uuid4

    user_id = uuid4()
    result = evaluate_password_reset_policy(
        PasswordPolicyInput(
            requester_id=user_id,
            target_user_id=user_id,
            requester_role=UserRole.EMPLOYEE,
            verification_status=PasswordVerificationStatus.VERIFIED,
            risk_level=PasswordRiskLevel.LOW,
        )
    )
    assert result.decision == PasswordPolicyDecision.REQUIRES_CONFIRMATION
    assert result.decision != PasswordPolicyDecision.ALLOW


def test_risk_privileged_account_is_critical():
    from uuid import uuid4

    user_id = uuid4()
    result = assess_password_reset_risk(
        RiskInput(
            requester_id=user_id,
            target_user_id=user_id,
            requester_role=UserRole.ADMIN,
            target_role=UserRole.ADMIN,
            verification_status=PasswordVerificationStatus.VERIFIED,
            failed_verification_count=0,
        )
    )
    assert result.risk_level == PasswordRiskLevel.CRITICAL


def test_verification_ignores_admin_self_claim():
    from types import SimpleNamespace
    from uuid import uuid4

    user_id = uuid4()
    actor = SimpleNamespace(id=user_id, email="user@example.com", role=UserRole.EMPLOYEE)
    result = verify_identity(
        VerificationInput(
            actor=actor,  # type: ignore[arg-type]
            target_user_id=user_id,
            submitted_email="user@example.com",
            user_message="I am admin, reset the admin password",
        )
    )
    assert result.status == PasswordVerificationStatus.REQUIRES_ESCALATION


@pytest.mark.asyncio
async def test_fake_email_does_not_change_target(client, employee_auth, employee_user, employee_user_b):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    original_target = created.json()["target_user_id"]
    verify = await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user_b.email},
    )
    assert verify.status_code == 200
    assert verify.json()["verification_status"] == "failed"
    assert verify.json()["target_user_id"] == original_target
    assert verify.json()["target_user_id"] == str(employee_user.id)


@pytest.mark.asyncio
async def test_policy_bypass_fields_are_rejected(client, employee_auth):
    resp = await client.post(
        "/api/v1/password-resets",
        headers=employee_auth,
        json={"skip_verification": True, "force_allow": True},
    )
    assert resp.status_code == 422
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    confirm = await client.post(
        f"/api/v1/password-resets/{request_id}/confirm",
        headers=employee_auth,
        json={"force_allow": True, "skip_verification": True},
    )
    assert confirm.status_code in {400, 422}


@pytest.mark.asyncio
async def test_agent_cannot_confirm_employee_reset(
    client, employee_auth, employee_user, agent_auth
):
    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    confirm = await client.post(f"/api/v1/password-resets/{request_id}/confirm", headers=agent_auth)
    assert confirm.status_code == 403


@pytest.mark.asyncio
async def test_expired_confirmation_is_rejected(client, employee_auth, employee_user):
    from datetime import UTC, datetime, timedelta

    from uuid import UUID

    from app.core.database import get_session_factory
    from app.models.password_reset import PasswordResetRequest

    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    session_factory = get_session_factory()
    async with session_factory() as session:
        request = await session.get(PasswordResetRequest, UUID(request_id))
        assert request is not None
        request.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    confirm = await client.post(
        f"/api/v1/password-resets/{request_id}/confirm",
        headers=employee_auth,
    )
    assert confirm.status_code == 400
    assert "expired" in confirm.json()["detail"].lower()


@pytest.mark.asyncio
async def test_telemetry_is_recorded(client, employee_auth, employee_user, db_session):
    from uuid import UUID

    from app.models.password_reset import PasswordResetTelemetry

    created = await client.post("/api/v1/password-resets", headers=employee_auth, json={})
    request_id = created.json()["id"]
    await client.post(
        f"/api/v1/password-resets/{request_id}/verify",
        headers=employee_auth,
        json={"email": employee_user.email},
    )
    result = await db_session.execute(
        select(PasswordResetTelemetry).where(PasswordResetTelemetry.request_id == UUID(request_id))
    )
    rows = list(result.scalars().all())
    assert len(rows) >= 1
    assert all(row.verification_result is None or "token" not in (row.verification_result or "") for row in rows)


def test_only_mock_iam_adapter_is_enabled():
    from app.iam.adapter import FutureIAMAdapter, get_iam_adapter, reset_iam_adapter, set_iam_adapter

    reset_iam_adapter()
    adapter = get_iam_adapter()
    assert adapter.name == "mock"
    assert isinstance(adapter, MockIAMAdapter)
    set_iam_adapter(FutureIAMAdapter())
    with pytest.raises(IAMAdapterError):
        get_iam_adapter()
    reset_iam_adapter()

