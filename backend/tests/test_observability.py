from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.ai.enums import AIModelType, AITaskType
from app.models.ai import AIInferenceTelemetry
from app.models.chat import ChatInteractionTelemetry, Conversation, ConversationStatus
from app.models.it_request import (
    ITPolicyDecision,
    ITRequest,
    ITRequestStatus,
    ITRequestType,
    ITRiskLevel,
    ITWorkflowTelemetry,
)
from app.models.password_reset import (
    PasswordPolicyDecision,
    PasswordResetRequest,
    PasswordResetStatus,
    PasswordResetTelemetry,
    PasswordRiskLevel,
    PasswordVerificationStatus,
)
from app.services.observability_service import ObservabilityService, _compare_anomaly
from tests.ai_fixtures import model_by_key

WINDOW = "range=custom&start=2015-06-01T00:00:00Z&end=2015-06-02T00:00:00Z"
EMPTY_WINDOW = "range=custom&start=2014-01-01T00:00:00Z&end=2014-01-02T00:00:00Z"
TS = datetime(2015, 6, 1, 12, 0, tzinfo=UTC)
BASELINE_TS = datetime(2015, 5, 28, 12, 0, tzinfo=UTC)

FORBIDDEN_KEYS = {
    "password",
    "password_hash",
    "jwt",
    "api_key",
    "secret",
    "access_token",
    "refresh_token",
    "iam_credentials",
    "shell_command",
}


def _keys(payload) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(key)
            found |= _keys(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= _keys(item)
    return found


def test_parse_window_defaults_and_custom():
    service = ObservabilityService()
    window = service.parse_window("7d")
    assert window.range == "7d"
    assert window.end > window.start
    custom = service.parse_window(
        "custom",
        datetime(2015, 6, 1, tzinfo=UTC),
        datetime(2015, 6, 2, tzinfo=UTC),
    )
    assert custom.range == "custom"
    with pytest.raises(ValueError):
        service.parse_window("custom")


def test_anomaly_detection_is_explainable():
    items = _compare_anomaly(
        "llm_p95_latency_ms",
        240.0,
        100.0,
        10,
        10,
        datetime(2015, 6, 1, tzinfo=UTC),
        "LLM p95 latency",
    )
    assert len(items) == 1
    assert items[0].severity == "warning"
    assert "2.4x" in items[0].explanation
    assert items[0].observed_value == 240.0
    assert items[0].baseline_value == 100.0

    assert _compare_anomaly("x", 240.0, 100.0, 2, 10, datetime.now(UTC), "x") == []
    assert _compare_anomaly("x", 240.0, 0.0, 10, 10, datetime.now(UTC), "x") == []
    assert _compare_anomaly("x", None, 100.0, 10, 10, datetime.now(UTC), "x") == []


@pytest.mark.asyncio
async def test_observability_rbac(client, employee_auth, agent_auth):
    employee = await client.get("/api/v1/observability/summary", headers=employee_auth)
    agent = await client.get("/api/v1/observability/summary", headers=agent_auth)
    anon = await client.get("/api/v1/observability/summary")
    assert employee.status_code == 403
    assert agent.status_code == 403
    assert anon.status_code == 401


@pytest.mark.asyncio
async def test_empty_telemetry_and_privacy(client, admin_auth):
    endpoints = [
        "summary",
        "models",
        "usage",
        "tokens",
        "cost",
        "latency",
        "rag",
        "chat",
        "it-workflows",
        "password-resets",
        "evaluations",
        "anomalies",
    ]
    for path in endpoints:
        resp = await client.get(f"/api/v1/observability/{path}?{EMPTY_WINDOW}", headers=admin_auth)
        assert resp.status_code == 200, path
        body = resp.json()
        assert FORBIDDEN_KEYS.isdisjoint(_keys(body))
        blob = str(body).lower()
        assert "password_hash" not in blob
        assert "sk-" not in blob

    summary = (
        await client.get(f"/api/v1/observability/summary?{EMPTY_WINDOW}", headers=admin_auth)
    ).json()
    assert summary["total_ai_requests"] == 0
    assert summary["success_rate"] is None
    assert summary["total_llm_tokens"] is None
    assert summary["estimated_cost_usd"] is None
    assert summary["empty"] is True

    tokens = (
        await client.get(f"/api/v1/observability/tokens?{EMPTY_WINDOW}", headers=admin_auth)
    ).json()
    assert tokens["total_tokens"] is None
    assert tokens["requests_with_usage"] == 0

    cost = (await client.get(f"/api/v1/observability/cost?{EMPTY_WINDOW}", headers=admin_auth)).json()
    assert cost["label"] == "Estimated Cost"
    assert cost["total_estimated_usd"] is None

    rag = (await client.get(f"/api/v1/observability/rag?{EMPTY_WINDOW}", headers=admin_auth)).json()
    assert rag["retrieval"]["precision_at_k"] == "Not evaluated"
    assert rag["generation"]["groundedness"] == "Not evaluated"

    chat = (await client.get(f"/api/v1/observability/chat?{EMPTY_WINDOW}", headers=admin_auth)).json()
    assert chat["messages"] == 0
    assert chat["escalation_rate"] is None

    workflows = (
        await client.get(f"/api/v1/observability/it-workflows?{EMPTY_WINDOW}", headers=admin_auth)
    ).json()
    assert "MOCK" in workflows["execution_mode"] or "SIMULATED" in workflows["execution_mode"]
    assert workflows["total_requests"] == 0

    resets = (
        await client.get(
            f"/api/v1/observability/password-resets?{EMPTY_WINDOW}", headers=admin_auth
        )
    ).json()
    assert "Mock IAM" in resets["execution_mode"]
    assert resets["total_requests"] == 0


@pytest.mark.asyncio
async def test_custom_range_requires_bounds(client, admin_auth):
    resp = await client.get("/api/v1/observability/summary?range=custom", headers=admin_auth)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_model_token_cost_latency_aggregation(
    client, db_session, admin_auth, ai_models
):
    llm = model_by_key(ai_models, "test-llm-v1")
    ml = model_by_key(ai_models, "test-ml-v1")
    latencies = [10.0, 20.0, 30.0, 40.0, 100.0]
    rows = []
    for index, latency in enumerate(latencies):
        model = llm if index < 4 else ml
        rows.append(
            AIInferenceTelemetry(
                request_id=uuid4(),
                model_registry_id=model.id,
                model_type=model.model_type,
                provider=model.provider,
                model_name=model.model_name,
                model_key=model.model_key,
                task=AITaskType.GENERATION.value if model.model_type == AIModelType.LLM else AITaskType.CLASSIFICATION.value,
                latency_ms=latency,
                success=index != 3,
                input_size=8,
                output_size=4,
                prompt_tokens=12 if index == 0 else None,
                completion_tokens=8 if index == 0 else None,
                total_tokens=20 if index == 0 else (0 if index == 1 else None),
                estimated_cost_usd=0.0015 if index == 0 else None,
                inference_units=1 if model.model_type != AIModelType.LLM else None,
                created_at=TS,
            )
        )
    db_session.add_all(rows)
    await db_session.commit()

    summary = (
        await client.get(f"/api/v1/observability/summary?{WINDOW}", headers=admin_auth)
    ).json()
    assert summary["total_ai_requests"] == 5
    assert summary["success_rate"] == pytest.approx(0.8)
    assert summary["average_latency_ms"] == pytest.approx(40.0)
    assert summary["p95_latency_ms"] is not None
    assert summary["p95_latency_ms"] >= summary["average_latency_ms"]
    assert summary["total_llm_tokens"] == 20
    assert summary["estimated_cost_usd"] == pytest.approx(0.0015)
    assert summary["cost_label"] == "Estimated Cost"

    models = (
        await client.get(f"/api/v1/observability/models?{WINDOW}", headers=admin_auth)
    ).json()["items"]
    by_key = {row["model_key"]: row for row in models}
    assert by_key["test-llm-v1"]["requests"] == 4
    assert by_key["test-ml-v1"]["requests"] == 1
    assert by_key["test-llm-v1"]["tokens_unknown_requests"] == 2
    assert by_key["test-llm-v1"]["total_tokens"] == 20
    assert by_key["test-ml-v1"]["prompt_tokens"] is None

    tokens = (await client.get(f"/api/v1/observability/tokens?{WINDOW}", headers=admin_auth)).json()
    assert tokens["prompt_tokens"] == 12
    assert tokens["completion_tokens"] == 8
    assert tokens["total_tokens"] == 20
    assert tokens["requests_with_usage"] == 2
    assert tokens["requests_without_usage"] == 3

    cost = (await client.get(f"/api/v1/observability/cost?{WINDOW}", headers=admin_auth)).json()
    assert cost["label"] == "Estimated Cost"
    assert cost["total_estimated_usd"] == pytest.approx(0.0015)
    assert cost["requests_without_cost"] == 4

    latency = (
        await client.get(f"/api/v1/observability/latency?{WINDOW}", headers=admin_auth)
    ).json()
    assert latency["overall"]["p50_ms"] == pytest.approx(30.0)
    assert latency["overall"]["min_ms"] == pytest.approx(10.0)
    assert latency["overall"]["max_ms"] == pytest.approx(100.0)
    assert latency["overall"]["p99_ms"] is not None

    usage = (await client.get(f"/api/v1/observability/usage?{WINDOW}", headers=admin_auth)).json()
    types = {item["name"]: item["count"] for item in usage["by_model_type"]}
    assert types["llm"] == 4
    assert types["lightweight_ml"] == 1


@pytest.mark.asyncio
async def test_evaluation_metrics_and_not_evaluated(
    client, admin_auth, ai_models
):
    ml = model_by_key(ai_models, "test-ml-v1")
    created = await client.post(
        f"/api/v1/ai/models/{ml.id}/evaluations",
        headers=admin_auth,
        json={
            "evaluation_type": "classification",
            "metrics": {
                "accuracy": 0.91,
                "precision": 0.88,
                "recall": 0.9,
                "f1_score": 0.89,
                "roc_auc": 0.93,
                "pr_auc": 0.87,
            },
            "dataset_ref": "intent-eval-v1",
            "sample_count": 40,
        },
    )
    assert created.status_code == 201

    body = (
        await client.get(f"/api/v1/observability/evaluations?{WINDOW}", headers=admin_auth)
    ).json()["items"]
    by_key = {row["model_key"]: row for row in body}
    assert by_key["test-ml-v1"]["classification"]["status"] == "evaluated"
    assert by_key["test-ml-v1"]["classification"]["metrics"]["accuracy"] == pytest.approx(0.91)
    assert by_key["test-ml-v1"]["regression"]["status"] == "Not evaluated"
    assert by_key["test-llm-v1"]["classification"]["status"] == "Not evaluated"
    assert by_key["test-llm-v1"]["llm_generation"]["status"] == "Not evaluated"


@pytest.mark.asyncio
async def test_chat_and_rag_metrics(client, db_session, admin_auth, employee_user):
    conversation = Conversation(
        user_id=employee_user.id,
        status=ConversationStatus.ACTIVE,
        created_at=TS,
    )
    db_session.add(conversation)
    await db_session.flush()
    db_session.add_all(
        [
            ChatInteractionTelemetry(
                conversation_id=conversation.id,
                user_id=employee_user.id,
                intent="knowledge_question",
                retrieval_latency_ms=40,
                generation_latency_ms=80,
                total_latency_ms=120,
                top_k=5,
                retrieved_count=4,
                top_similarity_score=0.82,
                citation_count=2,
                confidence_state="HIGH_CONFIDENCE",
                escalation_triggered=False,
                created_at=TS,
            ),
            ChatInteractionTelemetry(
                conversation_id=conversation.id,
                user_id=employee_user.id,
                intent="unsupported",
                retrieval_latency_ms=90,
                generation_latency_ms=20,
                total_latency_ms=110,
                top_k=5,
                retrieved_count=0,
                top_similarity_score=0.1,
                citation_count=0,
                confidence_state="NO_EVIDENCE",
                escalation_triggered=True,
                created_at=TS,
            ),
        ]
    )
    await db_session.commit()

    try:
        chat = (await client.get(f"/api/v1/observability/chat?{WINDOW}", headers=admin_auth)).json()
        assert chat["messages"] == 2
        assert chat["conversations"] == 1
        assert chat["escalations"] == 1
        assert chat["escalation_rate"] == pytest.approx(0.5)
        assert chat["citation_rate"] == pytest.approx(0.5)
        assert chat["unsupported_rate"] == pytest.approx(0.5)
        assert chat["latency"]["p50_ms"] is not None

        rag = (await client.get(f"/api/v1/observability/rag?{WINDOW}", headers=admin_auth)).json()
        assert rag["retrieval"]["interactions"] == 2
        assert rag["retrieval"]["mrr"] == "Not evaluated"
        assert rag["generation"]["faithfulness"] == "Not evaluated"
        assert rag["generation"]["citation_rate"] == pytest.approx(0.5)
    finally:
        await db_session.execute(
            delete(ChatInteractionTelemetry).where(ChatInteractionTelemetry.conversation_id == conversation.id)
        )
        await db_session.execute(delete(Conversation).where(Conversation.id == conversation.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_it_and_password_reset_metrics(client, db_session, admin_auth, employee_user):
    software = ITRequest(
        requester_id=employee_user.id,
        request_type=ITRequestType.SOFTWARE,
        status=ITRequestStatus.COMPLETED,
        requested_resource="vscode",
        user_message="install vscode",
        risk_level=ITRiskLevel.LOW,
        policy_decision=ITPolicyDecision.ALLOW,
        created_at=TS,
    )
    access = ITRequest(
        requester_id=employee_user.id,
        request_type=ITRequestType.ACCESS,
        status=ITRequestStatus.ESCALATED,
        requested_resource="finance-drive",
        user_message="need finance drive",
        risk_level=ITRiskLevel.HIGH,
        policy_decision=ITPolicyDecision.ESCALATE,
        created_at=TS,
    )
    db_session.add_all([software, access])
    await db_session.flush()
    db_session.add_all(
        [
            ITWorkflowTelemetry(
                request_id=software.id,
                user_id=employee_user.id,
                policy_latency_ms=12,
                planning_latency_ms=8,
                execution_latency_ms=30,
                validation_latency_ms=10,
                risk_level="low",
                policy_decision="allow",
                execution_status="success",
                validation_status="passed",
                created_at=TS,
            ),
            ITWorkflowTelemetry(
                request_id=access.id,
                user_id=employee_user.id,
                policy_latency_ms=15,
                risk_level="high",
                policy_decision="escalate",
                created_at=TS,
            ),
        ]
    )
    reset_ok = PasswordResetRequest(
        requester_id=employee_user.id,
        target_user_id=employee_user.id,
        status=PasswordResetStatus.COMPLETED,
        verification_status=PasswordVerificationStatus.VERIFIED,
        risk_level=PasswordRiskLevel.LOW,
        policy_decision=PasswordPolicyDecision.ALLOW,
        expires_at=TS + timedelta(hours=1),
        created_at=TS,
    )
    reset_fail = PasswordResetRequest(
        requester_id=employee_user.id,
        target_user_id=employee_user.id,
        status=PasswordResetStatus.VERIFICATION_FAILED,
        verification_status=PasswordVerificationStatus.FAILED,
        risk_level=PasswordRiskLevel.MEDIUM,
        policy_decision=PasswordPolicyDecision.DENY,
        expires_at=TS + timedelta(hours=1),
        created_at=TS,
    )
    db_session.add_all([reset_ok, reset_fail])
    await db_session.flush()
    db_session.add_all(
        [
            PasswordResetTelemetry(
                request_id=reset_ok.id,
                requester_id=employee_user.id,
                target_user_id=employee_user.id,
                workflow_stage="completed",
                verification_result="verified",
                risk_level="low",
                policy_decision="allow",
                verification_latency_ms=5,
                policy_latency_ms=4,
                iam_latency_ms=9,
                total_workflow_latency_ms=18,
                success=True,
                created_at=TS,
            ),
            PasswordResetTelemetry(
                request_id=reset_fail.id,
                requester_id=employee_user.id,
                target_user_id=employee_user.id,
                workflow_stage="verification_failed",
                verification_result="failed",
                risk_level="medium",
                policy_decision="deny",
                verification_latency_ms=6,
                success=False,
                created_at=TS,
            ),
        ]
    )
    await db_session.commit()

    try:
        workflows = (
            await client.get(f"/api/v1/observability/it-workflows?{WINDOW}", headers=admin_auth)
        ).json()
        assert workflows["total_requests"] == 2
        assert workflows["escalation_rate"] == pytest.approx(0.5)
        assert "MOCK" in workflows["execution_mode"] or "SIMULATED" in workflows["execution_mode"]
        types = {item["name"]: item["count"] for item in workflows["by_type"]}
        assert types["software"] == 1
        assert types["access"] == 1

        resets = (
            await client.get(
                f"/api/v1/observability/password-resets?{WINDOW}", headers=admin_auth
            )
        ).json()
        assert resets["total_requests"] == 2
        assert resets["verification_success_rate"] == pytest.approx(0.5)
        assert resets["verification_failure_rate"] == pytest.approx(0.5)
        assert "Mock IAM" in resets["execution_mode"]
        assert "password" not in _keys(resets)
        assert "password_hash" not in _keys(resets)
    finally:
        await db_session.execute(delete(ITWorkflowTelemetry).where(ITWorkflowTelemetry.request_id.in_([software.id, access.id])))
        await db_session.execute(delete(ITRequest).where(ITRequest.id.in_([software.id, access.id])))
        await db_session.execute(
            delete(PasswordResetTelemetry).where(
                PasswordResetTelemetry.request_id.in_([reset_ok.id, reset_fail.id])
            )
        )
        await db_session.execute(
            delete(PasswordResetRequest).where(PasswordResetRequest.id.in_([reset_ok.id, reset_fail.id]))
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_anomaly_latency_spike(client, db_session, admin_auth, ai_models):
    llm = model_by_key(ai_models, "test-llm-v1")
    for index in range(6):
        db_session.add(
            AIInferenceTelemetry(
                request_id=uuid4(),
                model_registry_id=llm.id,
                model_type=llm.model_type,
                provider=llm.provider,
                model_name=llm.model_name,
                model_key=llm.model_key,
                task=AITaskType.GENERATION.value,
                latency_ms=20,
                success=True,
                input_size=4,
                output_size=4,
                created_at=BASELINE_TS,
            )
        )
        db_session.add(
            AIInferenceTelemetry(
                request_id=uuid4(),
                model_registry_id=llm.id,
                model_type=llm.model_type,
                provider=llm.provider,
                model_name=llm.model_name,
                model_key=llm.model_key,
                task=AITaskType.GENERATION.value,
                latency_ms=80,
                success=True,
                input_size=4,
                output_size=4,
                created_at=TS,
            )
        )
    await db_session.commit()

    body = (
        await client.get(f"/api/v1/observability/anomalies?{WINDOW}", headers=admin_auth)
    ).json()
    metrics = {item["metric"]: item for item in body["items"]}
    assert "llm_p95_latency_ms" in metrics
    spike = metrics["llm_p95_latency_ms"]
    assert spike["observed_value"] > spike["baseline_value"]
    assert "baseline" in spike["explanation"]
    assert spike["severity"] in {"warning", "high", "critical"}
