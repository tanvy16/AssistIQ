"""Default AI model registry definitions and safe initialization.

Startup uses insert-if-missing only. The CLI seed script may force-upsert
the four default keys when an operator explicitly reseed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.enums import AIModelType, AITaskType
from app.models.ai import AIModelRegistry

logger = logging.getLogger("assistiq.ai.defaults")

DEFAULT_MODELS: list[dict[str, Any]] = [
    {
        "model_key": "local-logreg-v1",
        "model_type": AIModelType.LIGHTWEIGHT_ML,
        "provider": "local",
        "model_name": "logreg-keyword-v1",
        "version": 1,
        "capabilities": [
            AITaskType.CLASSIFICATION.value,
            AITaskType.INTENT_DETECTION.value,
            AITaskType.REGRESSION.value,
        ],
        "config_metadata": {"description": "Local keyword logistic-style classifier"},
    },
    {
        "model_key": "local-mlp-v1",
        "model_type": AIModelType.DEEP_LEARNING,
        "provider": "local",
        "model_name": "hash-embedding-mlp-v1",
        "version": 1,
        "capabilities": [
            AITaskType.CLASSIFICATION.value,
            AITaskType.INTENT_DETECTION.value,
        ],
        "config_metadata": {"description": "Local hash-embedding dense classifier"},
    },
    {
        "model_key": "openai-gpt4o-mini",
        "model_type": AIModelType.LLM,
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "version": 1,
        "capabilities": [
            AITaskType.GENERATION.value,
            AITaskType.SUMMARIZATION.value,
            AITaskType.INTENT_DETECTION.value,
            AITaskType.ENTITY_EXTRACTION.value,
            AITaskType.CLASSIFICATION.value,
        ],
        "config_metadata": {"description": "OpenAI-compatible LLM provider"},
    },
    {
        "model_key": "ollama-llama3.2",
        "model_type": AIModelType.LLM,
        "provider": "ollama",
        "model_name": "llama3.2:latest",
        "version": 1,
        "capabilities": [
            AITaskType.GENERATION.value,
            AITaskType.SUMMARIZATION.value,
            AITaskType.INTENT_DETECTION.value,
            AITaskType.ENTITY_EXTRACTION.value,
            AITaskType.CLASSIFICATION.value,
        ],
        "config_metadata": {"description": "Local Ollama OpenAI-compatible LLM"},
    },
]

DEFAULT_MODEL_KEYS = tuple(spec["model_key"] for spec in DEFAULT_MODELS)

SessionFactory = Callable[[], Any]


def _session_factory() -> async_sessionmaker[AsyncSession]:
    from app.core.database import get_session_factory

    return get_session_factory()


async def _get_by_key(session: AsyncSession, model_key: str) -> AIModelRegistry | None:
    result = await session.execute(
        select(AIModelRegistry).where(AIModelRegistry.model_key == model_key)
    )
    return result.scalar_one_or_none()


async def ensure_default_ai_models(
    session_factory: SessionFactory | None = None,
) -> dict[str, list[str]]:
    """Insert the four default registry keys if they are missing.

    Existing rows are left unchanged (enabled flag, provider, name, capabilities,
    and metadata). Repeated calls are safe and do not create duplicates.
    """
    factory = session_factory or _session_factory()
    inserted: list[str] = []
    skipped: list[str] = []
    async with factory() as session:
        for spec in DEFAULT_MODELS:
            existing = await _get_by_key(session, spec["model_key"])
            if existing is None:
                session.add(AIModelRegistry(enabled=True, **spec))
                inserted.append(spec["model_key"])
            else:
                skipped.append(spec["model_key"])
        await session.commit()
    logger.info(
        "AI model registry ensure completed",
        extra={"inserted": inserted, "skipped": skipped},
    )
    return {"inserted": inserted, "skipped": skipped}


async def reseed_default_ai_models(
    session_factory: SessionFactory | None = None,
) -> dict[str, list[str]]:
    """Force-upsert the four default keys. Intended for the CLI seed script only.

    Overwrites provider, model name, capabilities, metadata, and sets enabled=True
    on those keys. Does not delete other registry rows.
    """
    factory = session_factory or _session_factory()
    inserted: list[str] = []
    updated: list[str] = []
    async with factory() as session:
        for spec in DEFAULT_MODELS:
            existing = await _get_by_key(session, spec["model_key"])
            if existing is None:
                session.add(AIModelRegistry(enabled=True, **spec))
                inserted.append(spec["model_key"])
            else:
                existing.model_type = spec["model_type"]
                existing.provider = spec["provider"]
                existing.model_name = spec["model_name"]
                existing.capabilities = spec["capabilities"]
                existing.config_metadata = spec["config_metadata"]
                existing.enabled = True
                updated.append(spec["model_key"])
        await session.commit()
    logger.info(
        "AI model registry CLI reseed completed",
        extra={"inserted": inserted, "updated": updated},
    )
    return {"inserted": inserted, "updated": updated}
