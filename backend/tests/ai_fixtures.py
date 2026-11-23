import pytest
from sqlalchemy import delete, select

from app.ai.enums import AIModelType, AITaskType
from app.models.ai import AIEvaluationResult, AIInferenceTelemetry, AIModelRegistry


@pytest.fixture
async def ai_models(db_session):
    specs = [
        AIModelRegistry(
            model_key="test-ml-v1",
            model_type=AIModelType.LIGHTWEIGHT_ML,
            provider="local",
            model_name="logreg-test",
            version=1,
            enabled=True,
            capabilities=[AITaskType.CLASSIFICATION.value, AITaskType.REGRESSION.value],
        ),
        AIModelRegistry(
            model_key="test-dl-v1",
            model_type=AIModelType.DEEP_LEARNING,
            provider="local",
            model_name="mlp-test",
            version=1,
            enabled=True,
            capabilities=[AITaskType.CLASSIFICATION.value],
        ),
        AIModelRegistry(
            model_key="test-llm-v1",
            model_type=AIModelType.LLM,
            provider="openai",
            model_name="gpt-4o-mini",
            version=1,
            enabled=True,
            capabilities=[AITaskType.GENERATION.value],
        ),
        AIModelRegistry(
            model_key="test-disabled-v1",
            model_type=AIModelType.LIGHTWEIGHT_ML,
            provider="local",
            model_name="disabled",
            version=1,
            enabled=False,
            capabilities=[AITaskType.CLASSIFICATION.value],
        ),
    ]
    for spec in specs:
        result = await db_session.execute(
            select(AIModelRegistry).where(AIModelRegistry.model_key == spec.model_key)
        )
        if result.scalar_one_or_none() is None:
            db_session.add(spec)
    await db_session.commit()

    result = await db_session.execute(select(AIModelRegistry))
    models = list(result.scalars().all())
    yield models

    await db_session.execute(delete(AIEvaluationResult))
    await db_session.execute(delete(AIInferenceTelemetry))
    await db_session.execute(
        delete(AIModelRegistry).where(
            AIModelRegistry.model_key.in_(
                ["test-ml-v1", "test-dl-v1", "test-llm-v1", "test-disabled-v1"]
            )
        )
    )
    await db_session.commit()


def model_by_key(models, key: str) -> AIModelRegistry:
    return next(m for m in models if m.model_key == key)
