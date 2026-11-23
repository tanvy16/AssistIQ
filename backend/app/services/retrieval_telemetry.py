"""Internal retrieval telemetry (no LLM token metrics in Phase 4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger("assistiq.retrieval")


@dataclass
class RetrievalTelemetry:
    query: str
    top_k: int
    embedding_model_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    result_count: int = 0
    latency_ms: float = 0.0
    similarity_scores: list[float] = field(default_factory=list)

    def record(self) -> None:
        logger.info(
            "knowledge_retrieval",
            extra={
                "retrieval_timestamp": self.timestamp.isoformat(),
                "query_length": len(self.query),
                "top_k": self.top_k,
                "result_count": self.result_count,
                "latency_ms": round(self.latency_ms, 2),
                "embedding_model_id": self.embedding_model_id,
                "similarity_scores": [round(score, 4) for score in self.similarity_scores],
            },
        )
