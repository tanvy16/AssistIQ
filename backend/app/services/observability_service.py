"""Aggregate existing Phase 4–8 telemetry. Never fabricates tokens, scores, or cost."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIEvaluationResult, AIInferenceTelemetry, AIModelRegistry
from app.models.chat import ChatInteractionTelemetry, Conversation
from app.models.it_request import ITRequest, ITWorkflowTelemetry
from app.models.password_reset import PasswordResetRequest, PasswordResetTelemetry
from app.schemas.observability import (
    NOT_EVALUATED,
    Anomaly,
    ChatObservability,
    CostSummary,
    CountRate,
    EvaluationMetricSet,
    LatencyStats,
    ModelEvaluationRow,
    ModelUsageRow,
    NamedCount,
    ObservabilitySummary,
    PasswordResetObservability,
    RagObservability,
    TimePoint,
    TimeWindow,
    TokenSummary,
    WorkflowObservability,
)

ANOMALY_MULTIPLIER = 2.0
ANOMALY_MIN_SAMPLES = 5


class ObservabilityService:
    def parse_window(
        self,
        range_key: str = "7d",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> TimeWindow:
        now = datetime.now(UTC)
        mapping = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
        if range_key == "custom":
            if start is None or end is None:
                raise ValueError("Custom range requires start and end")
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)
            if end <= start:
                raise ValueError("end must be after start")
            return TimeWindow(range="custom", start=start, end=end)
        delta = mapping.get(range_key, mapping["7d"])
        key = range_key if range_key in mapping else "7d"
        return TimeWindow(range=key, start=now - delta, end=now)

    async def summary(self, db: AsyncSession, window: TimeWindow) -> ObservabilitySummary:
        from app.core.database import run_parallel_reads

        # Independent aggregates: run concurrently on separate pooled sessions.
        usage, latency, tokens, cost, chat = await run_parallel_reads(
            lambda s: self._inference_count_rate(s, window),
            lambda s: self._inference_latency(s, window),
            lambda s: self.tokens(s, window),
            lambda s: self.cost(s, window),
            lambda s: self.chat(s, window),
        )
        return ObservabilitySummary(
            window=window,
            total_ai_requests=usage.total,
            success_rate=usage.success_rate,
            average_latency_ms=latency.average_ms,
            p95_latency_ms=latency.p95_ms,
            total_llm_tokens=tokens.total_tokens,
            estimated_cost_usd=cost.total_estimated_usd,
            cost_label="Estimated Cost",
            escalation_rate=chat.escalation_rate,
            empty=usage.total == 0 and chat.messages == 0,
        )

    async def model_usage(self, db: AsyncSession, window: TimeWindow) -> list[ModelUsageRow]:
        stmt = (
            select(
                AIInferenceTelemetry.model_key,
                AIInferenceTelemetry.model_name,
                AIInferenceTelemetry.model_type,
                AIInferenceTelemetry.provider,
                func.count().label("requests"),
                func.sum(case((AIInferenceTelemetry.success.is_(True), 1), else_=0)).label("successful"),
                func.sum(case((AIInferenceTelemetry.success.is_(False), 1), else_=0)).label("failed"),
                func.avg(AIInferenceTelemetry.latency_ms).label("avg_latency"),
                func.percentile_cont(0.95).within_group(AIInferenceTelemetry.latency_ms).label("p95"),
                func.sum(AIInferenceTelemetry.prompt_tokens).label("prompt_tokens"),
                func.sum(AIInferenceTelemetry.completion_tokens).label("completion_tokens"),
                func.sum(AIInferenceTelemetry.total_tokens).label("total_tokens"),
                func.sum(case((AIInferenceTelemetry.total_tokens.is_(None), 1), else_=0)).label("tokens_unknown"),
                func.sum(AIInferenceTelemetry.estimated_cost_usd).label("cost"),
                func.sum(case((AIInferenceTelemetry.estimated_cost_usd.is_(None), 1), else_=0)).label("cost_unknown"),
                func.sum(AIInferenceTelemetry.inference_units).label("units"),
            )
            .where(self._in_window(AIInferenceTelemetry.created_at, window))
            .group_by(
                AIInferenceTelemetry.model_key,
                AIInferenceTelemetry.model_name,
                AIInferenceTelemetry.model_type,
                AIInferenceTelemetry.provider,
            )
            .order_by(func.count().desc())
        )
        rows = (await db.execute(stmt)).all()
        result: list[ModelUsageRow] = []
        for row in rows:
            requests = int(row.requests or 0)
            successful = int(row.successful or 0)
            result.append(
                ModelUsageRow(
                    model_key=row.model_key,
                    model_name=row.model_name,
                    model_type=row.model_type.value if hasattr(row.model_type, "value") else str(row.model_type),
                    provider=row.provider,
                    requests=requests,
                    successful=successful,
                    failed=int(row.failed or 0),
                    success_rate=_rate(successful, requests),
                    average_latency_ms=_float(row.avg_latency),
                    p95_latency_ms=_float(row.p95),
                    prompt_tokens=_int_or_none(row.prompt_tokens),
                    completion_tokens=_int_or_none(row.completion_tokens),
                    total_tokens=_int_or_none(row.total_tokens),
                    tokens_unknown_requests=int(row.tokens_unknown or 0),
                    estimated_cost_usd=_float(row.cost),
                    cost_unknown_requests=int(row.cost_unknown or 0),
                    inference_units=_int_or_none(row.units),
                )
            )
        return result

    async def usage_breakdown(self, db: AsyncSession, window: TimeWindow) -> dict[str, Any]:
        by_type = await self._group_count(db, AIInferenceTelemetry.model_type, window)
        by_provider = await self._group_count(db, AIInferenceTelemetry.provider, window)
        by_task = await self._group_count(db, AIInferenceTelemetry.task, window)
        over_time = await self._time_series_count(db, AIInferenceTelemetry.created_at, window)
        rate = await self._inference_count_rate(db, window)
        return {
            "counts": rate.model_dump(),
            "by_model_type": by_type,
            "by_provider": by_provider,
            "by_task": by_task,
            "over_time": over_time,
        }

    async def tokens(self, db: AsyncSession, window: TimeWindow) -> TokenSummary:
        where = and_(
            self._in_window(AIInferenceTelemetry.created_at, window),
            AIInferenceTelemetry.total_tokens.is_not(None),
        )
        totals = (
            await db.execute(
                select(
                    func.sum(AIInferenceTelemetry.prompt_tokens),
                    func.sum(AIInferenceTelemetry.completion_tokens),
                    func.sum(AIInferenceTelemetry.total_tokens),
                    func.count(),
                    func.avg(AIInferenceTelemetry.total_tokens),
                ).where(where)
            )
        ).one()
        unknown = (
            await db.execute(
                select(func.count()).where(
                    self._in_window(AIInferenceTelemetry.created_at, window),
                    AIInferenceTelemetry.total_tokens.is_(None),
                )
            )
        ).scalar_one()
        by_model_rows = (
            await db.execute(
                select(AIInferenceTelemetry.model_name, func.sum(AIInferenceTelemetry.total_tokens))
                .where(where)
                .group_by(AIInferenceTelemetry.model_name)
            )
        ).all()
        by_task_rows = (
            await db.execute(
                select(AIInferenceTelemetry.task, func.sum(AIInferenceTelemetry.total_tokens))
                .where(where)
                .group_by(AIInferenceTelemetry.task)
            )
        ).all()
        over_time = await self._time_series_sum(db, AIInferenceTelemetry.total_tokens, window)
        return TokenSummary(
            prompt_tokens=_int_or_none(totals[0]),
            completion_tokens=_int_or_none(totals[1]),
            total_tokens=_int_or_none(totals[2]),
            requests_with_usage=int(totals[3] or 0),
            requests_without_usage=int(unknown or 0),
            average_tokens_per_request=_float(totals[4]),
            by_model=[NamedCount(name=str(name), count=int(value or 0)) for name, value in by_model_rows],
            by_task=[NamedCount(name=str(name), count=int(value or 0)) for name, value in by_task_rows],
            over_time=over_time,
        )

    async def cost(self, db: AsyncSession, window: TimeWindow) -> CostSummary:
        where = and_(
            self._in_window(AIInferenceTelemetry.created_at, window),
            AIInferenceTelemetry.estimated_cost_usd.is_not(None),
        )
        totals = (
            await db.execute(
                select(
                    func.sum(AIInferenceTelemetry.estimated_cost_usd),
                    func.count(),
                    func.avg(AIInferenceTelemetry.estimated_cost_usd),
                ).where(where)
            )
        ).one()
        unknown = (
            await db.execute(
                select(func.count()).where(
                    self._in_window(AIInferenceTelemetry.created_at, window),
                    AIInferenceTelemetry.estimated_cost_usd.is_(None),
                )
            )
        ).scalar_one()
        by_model_rows = (
            await db.execute(
                select(AIInferenceTelemetry.model_name, func.sum(AIInferenceTelemetry.estimated_cost_usd))
                .where(where)
                .group_by(AIInferenceTelemetry.model_name)
            )
        ).all()
        by_task_rows = (
            await db.execute(
                select(AIInferenceTelemetry.task, func.sum(AIInferenceTelemetry.estimated_cost_usd))
                .where(where)
                .group_by(AIInferenceTelemetry.task)
            )
        ).all()
        return CostSummary(
            label="Estimated Cost",
            total_estimated_usd=_float(totals[0]),
            requests_with_cost=int(totals[1] or 0),
            requests_without_cost=int(unknown or 0),
            average_cost_per_request=_float(totals[2]),
            by_model=[
                NamedCount(name=str(name), count=0, extra={"estimated_usd": _float(value)})
                for name, value in by_model_rows
            ],
            by_task=[
                NamedCount(name=str(name), count=0, extra={"estimated_usd": _float(value)})
                for name, value in by_task_rows
            ],
            over_time=await self._time_series_sum(db, AIInferenceTelemetry.estimated_cost_usd, window),
        )

    async def latency(self, db: AsyncSession, window: TimeWindow) -> dict[str, Any]:
        overall = await self._inference_latency(db, window)
        by_model = await self.model_usage(db, window)
        return {
            "overall": overall.model_dump(),
            "by_model": [
                {"name": row.model_name, "average_ms": row.average_latency_ms, "p95_ms": row.p95_latency_ms}
                for row in by_model
            ],
            "over_time": await self._time_series_avg(db, AIInferenceTelemetry.latency_ms, window),
        }

    async def evaluations(self, db: AsyncSession, window: TimeWindow) -> list[ModelEvaluationRow]:
        models = (await db.execute(select(AIModelRegistry).order_by(AIModelRegistry.model_key))).scalars().all()
        usage = {row.model_key: row for row in await self.model_usage(db, window)}
        evals = (
            await db.execute(
                select(AIEvaluationResult).order_by(AIEvaluationResult.evaluated_at.desc())
            )
        ).scalars().all()
        latest: dict[tuple[UUID, str], AIEvaluationResult] = {}
        for record in evals:
            key = (record.model_registry_id, record.evaluation_type.value)
            if key not in latest:
                latest[key] = record

        rows: list[ModelEvaluationRow] = []
        for model in models:
            operational = usage.get(model.model_key)
            rows.append(
                ModelEvaluationRow(
                    model_id=str(model.id),
                    model_key=model.model_key,
                    model_name=model.model_name,
                    model_type=model.model_type.value,
                    classification=_eval_set(latest.get((model.id, "classification"))),
                    regression=_eval_set(latest.get((model.id, "regression"))),
                    llm_generation=_eval_set(latest.get((model.id, "llm_generation"))),
                    operational_latency=LatencyStats(
                        count=operational.requests if operational else 0,
                        average_ms=operational.average_latency_ms if operational else None,
                        p95_ms=operational.p95_latency_ms if operational else None,
                    ),
                    requests=operational.requests if operational else 0,
                )
            )
        return rows

    async def rag(self, db: AsyncSession, window: TimeWindow) -> RagObservability:
        retrieval = await self._latency_from(
            db, ChatInteractionTelemetry.retrieval_latency_ms, ChatInteractionTelemetry.created_at, window
        )
        averages = (
            await db.execute(
                select(
                    func.avg(ChatInteractionTelemetry.top_k),
                    func.avg(ChatInteractionTelemetry.retrieved_count),
                    func.avg(ChatInteractionTelemetry.top_similarity_score),
                    func.avg(ChatInteractionTelemetry.citation_count),
                    func.sum(case((ChatInteractionTelemetry.citation_count > 0, 1), else_=0)),
                    func.count(),
                ).where(self._in_window(ChatInteractionTelemetry.created_at, window))
            )
        ).one()
        count = int(averages[5] or 0)
        cited = int(averages[4] or 0)
        evals = await self.evaluations(db, window)
        generation_metrics: dict[str, Any] = {
            "groundedness": NOT_EVALUATED,
            "faithfulness": NOT_EVALUATED,
            "relevance": NOT_EVALUATED,
            "citation_correctness": NOT_EVALUATED,
            "citation_completeness": NOT_EVALUATED,
        }
        for row in evals:
            if row.llm_generation.status == "evaluated" and row.llm_generation.metrics:
                for key in generation_metrics:
                    if key in row.llm_generation.metrics:
                        generation_metrics[key] = row.llm_generation.metrics[key]
        return RagObservability(
            retrieval={
                "latency": retrieval.model_dump(),
                "average_top_k": _float(averages[0]),
                "average_retrieved_chunks": _float(averages[1]),
                "average_similarity": _float(averages[2]),
                "precision_at_k": NOT_EVALUATED,
                "recall_at_k": NOT_EVALUATED,
                "hit_rate_at_k": NOT_EVALUATED,
                "mrr": NOT_EVALUATED,
                "interactions": count,
            },
            generation={
                **generation_metrics,
                "citation_rate": _rate(cited, count),
                "average_citations": _float(averages[3]),
            },
            notes=(
                "Retrieval operational metrics come from chat telemetry. "
                "Precision@K, Recall@K, Hit Rate, MRR, groundedness, faithfulness, and relevance "
                "require ground-truth evaluation datasets."
            ),
        )

    async def chat(self, db: AsyncSession, window: TimeWindow) -> ChatObservability:
        conversations = (
            await db.execute(
                select(func.count()).where(self._in_window(Conversation.created_at, window))
            )
        ).scalar_one()
        total = (
            await db.execute(
                select(func.count()).where(self._in_window(ChatInteractionTelemetry.created_at, window))
            )
        ).scalar_one()
        escalations = (
            await db.execute(
                select(func.count()).where(
                    self._in_window(ChatInteractionTelemetry.created_at, window),
                    ChatInteractionTelemetry.escalation_triggered.is_(True),
                )
            )
        ).scalar_one()
        averages = (
            await db.execute(
                select(
                    func.avg(ChatInteractionTelemetry.retrieved_count),
                    func.avg(ChatInteractionTelemetry.top_similarity_score),
                    func.avg(ChatInteractionTelemetry.citation_count),
                    func.sum(case((ChatInteractionTelemetry.citation_count > 0, 1), else_=0)),
                    func.sum(case((ChatInteractionTelemetry.intent == "unsupported", 1), else_=0)),
                ).where(self._in_window(ChatInteractionTelemetry.created_at, window))
            )
        ).one()
        confidence = await self._named_counts(
            db, ChatInteractionTelemetry.confidence_state, ChatInteractionTelemetry.created_at, window
        )
        intents = await self._named_counts(
            db, ChatInteractionTelemetry.intent, ChatInteractionTelemetry.created_at, window
        )
        return ChatObservability(
            conversations=int(conversations or 0),
            messages=int(total or 0),
            latency=await self._latency_from(
                db, ChatInteractionTelemetry.total_latency_ms, ChatInteractionTelemetry.created_at, window
            ),
            retrieval_latency=await self._latency_from(
                db, ChatInteractionTelemetry.retrieval_latency_ms, ChatInteractionTelemetry.created_at, window
            ),
            generation_latency=await self._latency_from(
                db, ChatInteractionTelemetry.generation_latency_ms, ChatInteractionTelemetry.created_at, window
            ),
            average_retrieved_chunks=_float(averages[0]),
            average_similarity=_float(averages[1]),
            citation_rate=_rate(int(averages[3] or 0), int(total or 0)),
            average_citations=_float(averages[2]),
            escalation_rate=_rate(int(escalations or 0), int(total or 0)),
            escalations=int(escalations or 0),
            confidence=confidence,
            intents=intents,
            unsupported_rate=_rate(int(averages[4] or 0), int(total or 0)),
        )

    async def it_workflows(self, db: AsyncSession, window: TimeWindow) -> WorkflowObservability:
        total = (
            await db.execute(select(func.count()).where(self._in_window(ITRequest.created_at, window)))
        ).scalar_one()
        by_type = await self._named_counts(db, ITRequest.request_type, ITRequest.created_at, window)
        by_status = await self._named_counts(db, ITRequest.status, ITRequest.created_at, window)
        by_risk = await self._named_counts(db, ITRequest.risk_level, ITRequest.created_at, window)
        by_policy = await self._named_counts(db, ITRequest.policy_decision, ITRequest.created_at, window)
        counts = {item.name: item.count for item in by_policy}
        statuses = {item.name: item.count for item in by_status}
        n = int(total or 0)
        stage = (
            await db.execute(
                select(
                    func.avg(ITWorkflowTelemetry.policy_latency_ms),
                    func.avg(ITWorkflowTelemetry.planning_latency_ms),
                    func.avg(ITWorkflowTelemetry.execution_latency_ms),
                    func.avg(ITWorkflowTelemetry.validation_latency_ms),
                    func.avg(ITWorkflowTelemetry.rollback_latency_ms),
                    func.sum(case((ITWorkflowTelemetry.execution_status == "success", 1), else_=0)),
                    func.sum(case((ITWorkflowTelemetry.validation_status == "passed", 1), else_=0)),
                    func.sum(case((ITWorkflowTelemetry.rollback_status == "completed", 1), else_=0)),
                    func.count(),
                ).where(self._in_window(ITWorkflowTelemetry.created_at, window))
            )
        ).one()
        tel_n = int(stage[8] or 0)
        return WorkflowObservability(
            total_requests=n,
            by_type=by_type,
            by_status=by_status,
            by_risk=by_risk,
            by_policy=by_policy,
            policy_allow_rate=_rate(counts.get("allow", 0), n),
            approval_required_rate=_rate(counts.get("approval_required", 0), n),
            denial_rate=_rate(counts.get("deny", 0) + statuses.get("rejected", 0), n),
            escalation_rate=_rate(statuses.get("escalated", 0), n),
            execution_success_rate=_rate(int(stage[5] or 0), tel_n),
            validation_success_rate=_rate(int(stage[6] or 0), tel_n),
            rollback_rate=_rate(int(stage[7] or 0), tel_n),
            stage_latency={
                "policy_ms": _float(stage[0]),
                "planning_ms": _float(stage[1]),
                "execution_ms": _float(stage[2]),
                "validation_ms": _float(stage[3]),
                "rollback_ms": _float(stage[4]),
            },
            execution_mode="Execution is currently MOCK/SIMULATED. No real software was installed.",
        )

    async def password_resets(self, db: AsyncSession, window: TimeWindow) -> PasswordResetObservability:
        total = (
            await db.execute(
                select(func.count()).where(self._in_window(PasswordResetRequest.created_at, window))
            )
        ).scalar_one()
        by_status = await self._named_counts(
            db, PasswordResetRequest.status, PasswordResetRequest.created_at, window
        )
        by_risk = await self._named_counts(
            db, PasswordResetRequest.risk_level, PasswordResetRequest.created_at, window
        )
        by_policy = await self._named_counts(
            db, PasswordResetRequest.policy_decision, PasswordResetRequest.created_at, window
        )
        statuses = {item.name: item.count for item in by_status}
        n = int(total or 0)
        stage = (
            await db.execute(
                select(
                    func.avg(PasswordResetTelemetry.verification_latency_ms),
                    func.avg(PasswordResetTelemetry.policy_latency_ms),
                    func.avg(PasswordResetTelemetry.iam_latency_ms),
                    func.avg(PasswordResetTelemetry.total_workflow_latency_ms),
                    func.sum(case((PasswordResetTelemetry.verification_result == "verified", 1), else_=0)),
                    func.sum(case((PasswordResetTelemetry.verification_result == "failed", 1), else_=0)),
                    func.count(),
                ).where(self._in_window(PasswordResetTelemetry.created_at, window))
            )
        ).one()
        tel_n = int(stage[6] or 0)
        return PasswordResetObservability(
            total_requests=n,
            by_status=by_status,
            by_risk=by_risk,
            by_policy=by_policy,
            verification_success_rate=_rate(int(stage[4] or 0), tel_n),
            verification_failure_rate=_rate(int(stage[5] or 0), tel_n),
            confirmation_rate=_rate(statuses.get("confirmation_required", 0) + statuses.get("completed", 0), n),
            completion_rate=_rate(statuses.get("completed", 0), n),
            failure_rate=_rate(statuses.get("failed", 0) + statuses.get("verification_failed", 0), n),
            escalation_rate=_rate(statuses.get("escalated", 0), n),
            stage_latency={
                "verification_ms": _float(stage[0]),
                "policy_ms": _float(stage[1]),
                "iam_ms": _float(stage[2]),
                "total_ms": _float(stage[3]),
            },
        )

    async def anomalies(self, db: AsyncSession, window: TimeWindow) -> list[Anomaly]:
        baseline = TimeWindow(
            range="baseline",
            start=window.start - timedelta(days=7),
            end=window.start,
        )
        from app.core.database import run_parallel_reads

        (
            current_latency,
            baseline_latency,
            current_rate,
            baseline_rate,
            current_tokens,
            baseline_tokens,
            current_chat,
            baseline_chat,
        ) = await run_parallel_reads(
            lambda s: self._inference_latency(s, window),
            lambda s: self._inference_latency(s, baseline),
            lambda s: self._inference_count_rate(s, window),
            lambda s: self._inference_count_rate(s, baseline),
            lambda s: self.tokens(s, window),
            lambda s: self.tokens(s, baseline),
            lambda s: self.chat(s, window),
            lambda s: self.chat(s, baseline),
        )

        found: list[Anomaly] = []
        found.extend(
            _compare_anomaly(
                "llm_p95_latency_ms",
                current_latency.p95_ms,
                baseline_latency.p95_ms,
                current_latency.count,
                baseline_latency.count,
                window.end,
                "LLM p95 latency",
            )
        )
        found.extend(
            _compare_anomaly(
                "inference_failure_rate",
                1 - current_rate.success_rate if current_rate.success_rate is not None else None,
                1 - baseline_rate.success_rate if baseline_rate.success_rate is not None else None,
                current_rate.total,
                baseline_rate.total,
                window.end,
                "Inference failure rate",
            )
        )
        found.extend(
            _compare_anomaly(
                "llm_token_volume",
                float(current_tokens.total_tokens) if current_tokens.total_tokens is not None else None,
                float(baseline_tokens.total_tokens) if baseline_tokens.total_tokens is not None else None,
                current_tokens.requests_with_usage,
                baseline_tokens.requests_with_usage,
                window.end,
                "LLM token consumption",
            )
        )
        found.extend(
            _compare_anomaly(
                "chat_escalation_rate",
                current_chat.escalation_rate,
                baseline_chat.escalation_rate,
                current_chat.messages,
                baseline_chat.messages,
                window.end,
                "Chat escalation rate",
            )
        )
        found.extend(
            _compare_anomaly(
                "inference_request_volume",
                float(current_rate.total),
                float(baseline_rate.total),
                current_rate.total,
                baseline_rate.total,
                window.end,
                "AI request volume",
            )
        )
        found.extend(
            _compare_anomaly(
                "rag_retrieval_latency_ms",
                current_chat.retrieval_latency.p95_ms,
                baseline_chat.retrieval_latency.p95_ms,
                current_chat.retrieval_latency.count,
                baseline_chat.retrieval_latency.count,
                window.end,
                "RAG retrieval latency",
            )
        )
        return found

    def _in_window(self, column, window: TimeWindow):
        return and_(column >= window.start, column < window.end)

    async def _inference_count_rate(self, db: AsyncSession, window: TimeWindow) -> CountRate:
        row = (
            await db.execute(
                select(
                    func.count(),
                    func.sum(case((AIInferenceTelemetry.success.is_(True), 1), else_=0)),
                    func.sum(case((AIInferenceTelemetry.success.is_(False), 1), else_=0)),
                ).where(self._in_window(AIInferenceTelemetry.created_at, window))
            )
        ).one()
        total = int(row[0] or 0)
        successful = int(row[1] or 0)
        failed = int(row[2] or 0)
        return CountRate(
            total=total,
            successful=successful,
            failed=failed,
            success_rate=_rate(successful, total),
        )

    async def _inference_latency(self, db: AsyncSession, window: TimeWindow) -> LatencyStats:
        return await self._latency_from(db, AIInferenceTelemetry.latency_ms, AIInferenceTelemetry.created_at, window)

    async def _latency_from(self, db: AsyncSession, column, time_column, window: TimeWindow) -> LatencyStats:
        row = (
            await db.execute(
                select(
                    func.count(column),
                    func.avg(column),
                    func.min(column),
                    func.max(column),
                    func.percentile_cont(0.5).within_group(column),
                    func.percentile_cont(0.95).within_group(column),
                    func.percentile_cont(0.99).within_group(column),
                ).where(self._in_window(time_column, window), column.is_not(None))
            )
        ).one()
        return LatencyStats(
            count=int(row[0] or 0),
            average_ms=_float(row[1]),
            min_ms=_float(row[2]),
            max_ms=_float(row[3]),
            p50_ms=_float(row[4]),
            p95_ms=_float(row[5]),
            p99_ms=_float(row[6]),
        )

    async def _group_count(self, db: AsyncSession, column, window: TimeWindow) -> list[dict[str, Any]]:
        rows = (
            await db.execute(
                select(column, func.count())
                .where(self._in_window(AIInferenceTelemetry.created_at, window))
                .group_by(column)
            )
        ).all()
        return [{"name": _enum_name(name), "count": int(count)} for name, count in rows]

    async def _named_counts(self, db: AsyncSession, column, time_column, window: TimeWindow) -> list[NamedCount]:
        rows = (
            await db.execute(
                select(column, func.count())
                .where(self._in_window(time_column, window), column.is_not(None))
                .group_by(column)
            )
        ).all()
        return [NamedCount(name=_enum_name(name), count=int(count)) for name, count in rows]

    async def _time_series_count(self, db: AsyncSession, column, window: TimeWindow) -> list[TimePoint]:
        bucket = func.date_trunc("day", column)
        rows = (
            await db.execute(
                select(bucket, func.count())
                .where(self._in_window(column, window))
                .group_by(bucket)
                .order_by(bucket)
            )
        ).all()
        return [TimePoint(bucket=_aware(ts), count=int(count), value=float(count)) for ts, count in rows if ts]

    async def _time_series_sum(self, db: AsyncSession, value_column, window: TimeWindow) -> list[TimePoint]:
        bucket = func.date_trunc("day", AIInferenceTelemetry.created_at)
        rows = (
            await db.execute(
                select(bucket, func.sum(value_column), func.count())
                .where(self._in_window(AIInferenceTelemetry.created_at, window), value_column.is_not(None))
                .group_by(bucket)
                .order_by(bucket)
            )
        ).all()
        return [
            TimePoint(bucket=_aware(ts), value=_float(value), count=int(count or 0))
            for ts, value, count in rows
            if ts
        ]

    async def _time_series_avg(self, db: AsyncSession, value_column, window: TimeWindow) -> list[TimePoint]:
        bucket = func.date_trunc("day", AIInferenceTelemetry.created_at)
        rows = (
            await db.execute(
                select(bucket, func.avg(value_column), func.count())
                .where(self._in_window(AIInferenceTelemetry.created_at, window), value_column.is_not(None))
                .group_by(bucket)
                .order_by(bucket)
            )
        ).all()
        return [
            TimePoint(bucket=_aware(ts), value=_float(value), count=int(count or 0))
            for ts, value, count in rows
            if ts
        ]


def _rate(part: int, whole: int) -> float | None:
    if whole <= 0:
        return None
    return part / whole


def _float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _enum_name(value: Any) -> str:
    if value is None:
        return "unknown"
    return value.value if hasattr(value, "value") else str(value)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _eval_set(record: AIEvaluationResult | None) -> EvaluationMetricSet:
    if record is None:
        return EvaluationMetricSet(status=NOT_EVALUATED)
    return EvaluationMetricSet(
        status="evaluated",
        metrics=record.metrics,
        dataset_ref=record.dataset_ref,
        sample_count=record.sample_count,
        evaluated_at=record.evaluated_at,
    )


def _compare_anomaly(
    metric: str,
    observed: float | None,
    baseline: float | None,
    observed_n: int,
    baseline_n: int,
    timestamp: datetime,
    label: str,
) -> list[Anomaly]:
    if observed is None or baseline is None:
        return []
    if observed_n < ANOMALY_MIN_SAMPLES or baseline_n < ANOMALY_MIN_SAMPLES:
        return []
    if baseline <= 0:
        return []
    ratio = observed / baseline
    if ratio < ANOMALY_MULTIPLIER:
        return []
    severity: str = "warning"
    if ratio >= 5:
        severity = "critical"
    elif ratio >= 3:
        severity = "high"
    return [
        Anomaly(
            metric=metric,
            observed_value=round(observed, 4),
            baseline_value=round(baseline, 4),
            severity=severity,  # type: ignore[arg-type]
            timestamp=timestamp,
            explanation=f"{label} increased {ratio:.1f}x above the 7-day baseline.",
        )
    ]


_observability_service: ObservabilityService | None = None


def get_observability_service() -> ObservabilityService:
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityService()
    return _observability_service


def reset_observability_service() -> None:
    global _observability_service
    _observability_service = None
