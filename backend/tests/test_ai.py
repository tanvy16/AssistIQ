import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.ai.adapters.base import ModelAdapterError

from app.ai.adapters.deep_learning import DeepLearningAdapter
from app.ai.adapters.lightweight_ml import LightweightMLAdapter
from app.ai.adapters.llm import LLMAdapter
from app.ai.enums import AIModelType, AIEvaluationType, AITaskType
from app.ai.registry import AdapterFactory
from app.ai.schemas import AIInferenceInput
from app.models.ai import AIInferenceTelemetry
from tests.ai_fixtures import model_by_key


@pytest.mark.asyncio
async def test_list_models_excludes_disabled_for_employee(client, employee_auth, ai_models):
    resp = await client.get("/api/v1/ai/models", headers=employee_auth)
    assert resp.status_code == 200
    keys = {item["model_key"] for item in resp.json()["items"]}
    assert "test-disabled-v1" not in keys
    assert "test-ml-v1" in keys


@pytest.mark.asyncio
async def test_admin_lists_disabled_models(client, admin_auth, ai_models):
    resp = await client.get("/api/v1/ai/models", headers=admin_auth)
    assert resp.status_code == 200
    keys = {item["model_key"] for item in resp.json()["items"]}
    assert "test-disabled-v1" in keys


@pytest.mark.asyncio
async def test_admin_can_toggle_model(client, admin_auth, ai_models):
    disabled = model_by_key(ai_models, "test-disabled-v1")
    resp = await client.patch(
        f"/api/v1/ai/models/{disabled.id}",
        headers=admin_auth,
        json={"enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


@pytest.mark.asyncio
async def test_employee_cannot_toggle_model(client, employee_auth, ai_models):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.patch(
        f"/api/v1/ai/models/{model.id}",
        headers=employee_auth,
        json={"enabled": False},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_infer_lightweight_ml_records_telemetry(
    client, db_session, admin_auth, ai_models
):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        "/api/v1/ai/infer",
        headers=admin_auth,
        json={
            "model_id": str(model.id),
            "task": "classification",
            "input": {"text": "VPN connection failing on corporate network"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_type"] == "lightweight_ml"
    assert body["output"]["label"] == "network"
    assert body["usage"]["inference_units"] is not None
    assert body["usage"]["prompt_tokens"] is None

    telemetry = await db_session.scalar(
        select(AIInferenceTelemetry).where(
            AIInferenceTelemetry.request_id == uuid.UUID(body["request_id"])
        )
    )
    assert telemetry is not None
    assert telemetry.success is True
    assert telemetry.inference_units is not None
    assert telemetry.prompt_tokens is None


@pytest.mark.asyncio
async def test_infer_deep_learning(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-dl-v1")
    resp = await client.post(
        "/api/v1/ai/infer",
        headers=admin_auth,
        json={
            "model_id": str(model.id),
            "task": "classification",
            "input": {"text": "Need password reset for my account"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["model_type"] == "deep_learning"
    assert "label" in resp.json()["output"]


@pytest.mark.asyncio
async def test_infer_llm_records_token_telemetry(
    client, db_session, admin_auth, ai_models, monkeypatch
):
    model = model_by_key(ai_models, "test-llm-v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "choices": [{"message": {"content": "Summary complete."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }

    with patch("app.ai.adapters.llm.get_llm_http_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        from app.core.config import get_settings

        get_settings.cache_clear()
        from app.ai.registry import reset_adapter_factory

        reset_adapter_factory()
        resp = await client.post(
            "/api/v1/ai/infer",
            headers=admin_auth,
            json={
                "model_id": str(model.id),
                "task": "generation",
                "input": {"text": "Summarize VPN troubleshooting steps"},
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["usage"]["total_tokens"] == 20
    assert body["usage"]["prompt_tokens"] == 12

    telemetry = await db_session.scalar(
        select(AIInferenceTelemetry).where(
            AIInferenceTelemetry.request_id == uuid.UUID(body["request_id"])
        )
    )
    assert telemetry.total_tokens == 20
    assert telemetry.inference_units is None


@pytest.mark.asyncio
async def test_infer_disabled_model_rejected(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-disabled-v1")
    resp = await client.post(
        "/api/v1/ai/infer",
        headers=admin_auth,
        json={
            "model_id": str(model.id),
            "task": "classification",
            "input": {"text": "printer jam"},
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_infer_empty_input_rejected(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        "/api/v1/ai/infer",
        headers=admin_auth,
        json={"model_id": str(model.id), "task": "classification", "input": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_infer_failure_records_telemetry(client, db_session, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        "/api/v1/ai/infer",
        headers=admin_auth,
        json={
            "model_id": str(model.id),
            "task": "classification",
            "input": {"text": "   "},
        },
    )
    assert resp.status_code == 400
    result = await db_session.execute(
        select(AIInferenceTelemetry).where(AIInferenceTelemetry.success.is_(False))
    )
    assert result.scalars().first() is not None


@pytest.mark.asyncio
async def test_record_classification_evaluation(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        f"/api/v1/ai/models/{model.id}/evaluations",
        headers=admin_auth,
        json={
            "evaluation_type": "classification",
            "metrics": {
                "accuracy": 0.91,
                "precision": 0.88,
                "recall": 0.86,
                "f1_score": 0.87,
                "latency_ms": 12.5,
            },
            "dataset_ref": "ticket-dev-sample",
            "sample_count": 250,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["metrics"]["f1_score"] == 0.87


@pytest.mark.asyncio
async def test_record_llm_evaluation_metrics(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-llm-v1")
    resp = await client.post(
        f"/api/v1/ai/models/{model.id}/evaluations",
        headers=admin_auth,
        json={
            "evaluation_type": "llm_generation",
            "metrics": {
                "groundedness": 0.82,
                "relevance": 0.88,
                "latency_ms": 1200,
                "total_tokens": 450,
            },
            "sample_count": 30,
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_invalid_evaluation_metrics_rejected(client, admin_auth, ai_models):
    model = model_by_key(ai_models, "test-ml-v1")
    resp = await client.post(
        f"/api/v1/ai/models/{model.id}/evaluations",
        headers=admin_auth,
        json={"evaluation_type": "classification", "metrics": {"made_up_score": 1.0}},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_adapter_factory_returns_three_types():
    factory = AdapterFactory()
    assert isinstance(factory.get_adapter(AIModelType.LIGHTWEIGHT_ML), LightweightMLAdapter)
    assert isinstance(factory.get_adapter(AIModelType.DEEP_LEARNING), DeepLearningAdapter)
    assert isinstance(factory.get_adapter(AIModelType.LLM), LLMAdapter)


@pytest.mark.asyncio
async def test_lightweight_ml_adapter_classification():
    adapter = LightweightMLAdapter()
    output = await adapter.infer(
        AIInferenceInput(
            task=AITaskType.CLASSIFICATION,
            model_type=AIModelType.LIGHTWEIGHT_ML,
            provider="local",
            model_name="test",
            input_data={"text": "software install failing"},
        )
    )
    assert output.output["label"] == "software"


@pytest.mark.asyncio
async def test_llm_without_api_key_fails(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    adapter = LLMAdapter()
    with pytest.raises(ModelAdapterError):
        await adapter.infer(
            AIInferenceInput(
                task=AITaskType.GENERATION,
                model_type=AIModelType.LLM,
                provider="openai",
                model_name="gpt-4o-mini",
                input_data={"text": "hello"},
            )
        )
