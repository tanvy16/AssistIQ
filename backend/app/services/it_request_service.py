"""IT request orchestration: extract → policy → approve → plan → mock execute."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.execution.adapter import get_execution_adapter
from app.models.enums import UserRole
from app.models.it_request import (
    AccessCatalog,
    ITApprovalStatus,
    ITExecutionStatus,
    ITPolicyDecision,
    ITRequest,
    ITRequestStatus,
    ITRequestType,
    ITRiskLevel,
    ITWorkflowTelemetry,
    RequestApproval,
    RequestEntity,
    RequestEvent,
    Runbook,
    RunbookExecution,
    SoftwareCatalog,
)
from app.models.user import User
from app.runbooks.base import RunbookDisabledError, RunbookValidationError, UnknownRunbookError
from app.runbooks.registry import get_runbook
from app.services.entity_extraction import CatalogMatch, ExtractionResult, extract_entities
from app.services.planner_service import build_plan
from app.services.policy_service import PolicyInput, evaluate_policy
from app.services.audit_service import record_audit_event


class ITRequestError(Exception):
    pass


class ITRequestNotFoundError(ITRequestError):
    pass


class ITRequestAccessDeniedError(ITRequestError):
    pass


class ITRequestValidationError(ITRequestError):
    pass


class ITRequestService:
    async def create_request(
        self,
        db: AsyncSession,
        *,
        actor: User,
        message: str,
        request_type: ITRequestType | None = None,
        conversation_id: uuid.UUID | None = None,
        force_failure: bool = False,
    ) -> ITRequest:
        text = message.strip()
        if not text:
            raise ITRequestValidationError("Request message must not be empty")

        catalog = await self._load_catalog_matches(db)
        extraction = extract_entities(text, catalog)
        if request_type is not None:
            extraction.request_type = request_type

        request = ITRequest(
            requester_id=actor.id,
            conversation_id=conversation_id,
            request_type=extraction.request_type,
            status=ITRequestStatus.SUBMITTED,
            requested_resource=extraction.resource,
            justification=extraction.justification,
            risk_level=ITRiskLevel.MEDIUM,
            user_message=text,
            extraction_confidence=extraction.confidence,
            catalog_kind=extraction.catalog_kind,
            catalog_item_id=uuid.UUID(extraction.catalog_item_id) if extraction.catalog_item_id else None,
            selected_runbook_id=extraction.catalog_runbook_id,
        )
        db.add(request)
        await db.flush()
        await self._add_event(db, request, "request.created", actor.id, {"source": "api" if not conversation_id else "chat"})

        for entity in extraction.entities:
            db.add(
                RequestEntity(
                    request_id=request.id,
                    entity_type=entity.entity_type,
                    entity_name=entity.entity_name,
                    entity_value=entity.entity_value,
                    confidence=entity.confidence,
                    source=entity.source,
                )
            )
        await self._add_event(
            db,
            request,
            "request.entities_extracted",
            actor.id,
            {"confidence": extraction.confidence, "count": len(extraction.entities)},
        )
        request.status = ITRequestStatus.PARSED

        if extraction.needs_clarification:
            request.status = ITRequestStatus.ESCALATED
            request.policy_decision = ITPolicyDecision.ESCALATE
            await self._add_event(
                db,
                request,
                "request.escalated",
                actor.id,
                {"reason": "low_confidence_extraction"},
            )
            await db.commit()
            return await self.get_request(db, actor=actor, request_id=request.id)

        await self._apply_policy_and_maybe_execute(
            db, request=request, extraction=extraction, actor=actor, force_failure=force_failure
        )
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def list_requests(self, db: AsyncSession, *, actor: User) -> list[ITRequest]:
        query = select(ITRequest).order_by(ITRequest.created_at.desc())
        if actor.role == UserRole.EMPLOYEE:
            query = query.where(ITRequest.requester_id == actor.id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_request(self, db: AsyncSession, *, actor: User, request_id: uuid.UUID) -> ITRequest:
        result = await db.execute(
            select(ITRequest)
            .where(ITRequest.id == request_id)
            .options(
                selectinload(ITRequest.entities),
                selectinload(ITRequest.approvals),
                selectinload(ITRequest.executions),
                selectinload(ITRequest.events),
            )
            .execution_options(populate_existing=True)
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise ITRequestNotFoundError("IT request not found")
        self._ensure_access(actor, request)
        return request

    async def list_events(self, db: AsyncSession, *, actor: User, request_id: uuid.UUID) -> list[RequestEvent]:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        result = await db.execute(
            select(RequestEvent)
            .where(RequestEvent.request_id == request.id)
            .order_by(RequestEvent.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_execution(
        self, db: AsyncSession, *, actor: User, request_id: uuid.UUID
    ) -> RunbookExecution | None:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        result = await db.execute(
            select(RunbookExecution)
            .where(RunbookExecution.request_id == request.id)
            .order_by(RunbookExecution.started_at.desc())
        )
        return result.scalars().first()

    async def approve(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
        comment: str | None = None,
    ) -> ITRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        self._ensure_can_approve(actor, request)
        if request.status != ITRequestStatus.APPROVAL_REQUIRED:
            raise ITRequestValidationError("Request is not awaiting approval")

        request.status = ITRequestStatus.APPROVED
        db.add(
            RequestApproval(
                request_id=request.id,
                approver_id=actor.id,
                status=ITApprovalStatus.APPROVED,
                decision="approved",
                comment=comment,
            )
        )
        await self._add_event(db, request, "request.approved", actor.id, {"comment": comment})
        extraction = await self._extraction_from_request(db, request)
        await self._run_plan_and_execute(db, request=request, extraction=extraction, actor=actor)
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def reject(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
        comment: str | None = None,
    ) -> ITRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        self._ensure_can_approve(actor, request)
        if request.status not in {ITRequestStatus.APPROVAL_REQUIRED, ITRequestStatus.SUBMITTED, ITRequestStatus.PARSED}:
            raise ITRequestValidationError("Request cannot be rejected in its current state")
        request.status = ITRequestStatus.REJECTED
        request.completed_at = datetime.now(UTC)
        db.add(
            RequestApproval(
                request_id=request.id,
                approver_id=actor.id,
                status=ITApprovalStatus.REJECTED,
                decision="rejected",
                comment=comment,
            )
        )
        await self._add_event(db, request, "request.rejected", actor.id, {"comment": comment})
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def cancel(self, db: AsyncSession, *, actor: User, request_id: uuid.UUID) -> ITRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        if actor.role == UserRole.EMPLOYEE and request.requester_id != actor.id:
            raise ITRequestAccessDeniedError("You can only cancel your own requests")
        cancellable = {
            ITRequestStatus.SUBMITTED,
            ITRequestStatus.PARSED,
            ITRequestStatus.POLICY_REVIEW,
            ITRequestStatus.APPROVAL_REQUIRED,
        }
        if request.status not in cancellable:
            raise ITRequestValidationError("Request can no longer be cancelled")
        request.status = ITRequestStatus.CANCELLED
        request.completed_at = datetime.now(UTC)
        await self._add_event(db, request, "request.cancelled", actor.id, None)
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def list_software_catalog(self, db: AsyncSession) -> list[SoftwareCatalog]:
        result = await db.execute(select(SoftwareCatalog).order_by(SoftwareCatalog.name))
        return list(result.scalars().all())

    async def list_access_catalog(self, db: AsyncSession) -> list[AccessCatalog]:
        result = await db.execute(select(AccessCatalog).order_by(AccessCatalog.resource_name))
        return list(result.scalars().all())

    async def list_runbooks(self, db: AsyncSession) -> list[Runbook]:
        result = await db.execute(select(Runbook).order_by(Runbook.id))
        return list(result.scalars().all())

    async def set_catalog_enabled(
        self,
        db: AsyncSession,
        *,
        actor: User,
        kind: str,
        item_id: uuid.UUID,
        enabled: bool,
    ):
        if actor.role != UserRole.ADMIN:
            raise ITRequestAccessDeniedError("Only admins can manage catalogs")
        model = SoftwareCatalog if kind == "software" else AccessCatalog
        result = await db.execute(select(model).where(model.id == item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise ITRequestNotFoundError("Catalog item not found")
        item.enabled = enabled
        await db.commit()
        await db.refresh(item)
        return item

    async def set_runbook_enabled(self, db: AsyncSession, *, actor: User, runbook_id: str, enabled: bool) -> Runbook:
        if actor.role != UserRole.ADMIN:
            raise ITRequestAccessDeniedError("Only admins can manage runbooks")
        result = await db.execute(select(Runbook).where(Runbook.id == runbook_id))
        runbook = result.scalar_one_or_none()
        if runbook is None:
            raise ITRequestNotFoundError("Runbook not found")
        runbook.enabled = enabled
        await db.commit()
        await db.refresh(runbook)
        return runbook

    async def _apply_policy_and_maybe_execute(
        self,
        db: AsyncSession,
        *,
        request: ITRequest,
        extraction: ExtractionResult,
        actor: User,
        force_failure: bool = False,
    ) -> None:
        request.status = ITRequestStatus.POLICY_REVIEW
        started = time.perf_counter()
        catalog_risk = ITRiskLevel(extraction.catalog_risk) if extraction.catalog_risk else None
        policy = evaluate_policy(
            PolicyInput(
                request_type=extraction.request_type,
                user_message=request.user_message,
                catalog_matched=extraction.catalog_item_id is not None,
                catalog_enabled=extraction.catalog_enabled,
                catalog_risk=catalog_risk,
                catalog_approval_required=extraction.catalog_approval_required,
                resource=extraction.resource,
            )
        )
        policy_ms = (time.perf_counter() - started) * 1000
        request.policy_decision = policy.decision
        request.risk_level = policy.risk_level
        request.approval_required = policy.approval_required

        event_map = {
            ITPolicyDecision.ALLOW: "request.policy_allowed",
            ITPolicyDecision.DENY: "request.policy_denied",
            ITPolicyDecision.APPROVAL_REQUIRED: "request.approval_required",
            ITPolicyDecision.ESCALATE: "request.escalated",
        }
        await self._add_event(db, request, event_map[policy.decision], actor.id, {"reason": policy.reason})

        if policy.decision == ITPolicyDecision.DENY:
            request.status = ITRequestStatus.REJECTED
            request.completed_at = datetime.now(UTC)
        elif policy.decision == ITPolicyDecision.ESCALATE:
            request.status = ITRequestStatus.ESCALATED
        elif policy.decision == ITPolicyDecision.APPROVAL_REQUIRED:
            request.status = ITRequestStatus.APPROVAL_REQUIRED
        else:
            await self._run_plan_and_execute(
                db, request=request, extraction=extraction, actor=actor, force_failure=force_failure
            )

        db.add(
            ITWorkflowTelemetry(
                request_id=request.id,
                user_id=actor.id,
                policy_latency_ms=policy_ms,
                risk_level=policy.risk_level.value,
                policy_decision=policy.decision.value,
                approval_required=policy.approval_required,
            )
        )

    async def _run_plan_and_execute(
        self,
        db: AsyncSession,
        *,
        request: ITRequest,
        extraction: ExtractionResult,
        actor: User,
        force_failure: bool = False,
    ) -> None:
        if request.policy_decision != ITPolicyDecision.ALLOW and request.status != ITRequestStatus.APPROVED:
            raise ITRequestValidationError(
                "Execution is not permitted without a policy allow decision or recorded approval"
            )

        db_runbook = None
        if request.selected_runbook_id:
            result = await db.execute(select(Runbook).where(Runbook.id == request.selected_runbook_id))
            db_runbook = result.scalar_one_or_none()
            if db_runbook is None:
                raise UnknownRunbookError("Unknown runbook")
            if not db_runbook.enabled:
                raise RunbookDisabledError("Runbook is disabled")

        plan_started = time.perf_counter()
        plan = build_plan(
            runbook_id=request.selected_runbook_id,
            request_type=request.request_type,
            resource=request.requested_resource,
            catalog_matched=request.catalog_item_id is not None,
        )
        request.plan = plan
        request.status = ITRequestStatus.PLANNED
        await self._add_event(db, request, "request.planned", actor.id, {"runbook_id": request.selected_runbook_id})
        planning_ms = (time.perf_counter() - plan_started) * 1000

        handler = get_runbook(request.selected_runbook_id)  # type: ignore[arg-type]
        context = {
            "runbook_id": request.selected_runbook_id,
            "resource": request.requested_resource,
            "force_failure": force_failure,
        }
        handler.validate(context)
        expected = handler.expected_result(context)

        request.status = ITRequestStatus.EXECUTING
        await self._add_event(db, request, "request.execution_started", actor.id, {"adapter": "mock"})
        exec_started = time.perf_counter()
        adapter = get_execution_adapter()
        result = await adapter.execute(
            runbook_id=request.selected_runbook_id or "",
            expected=expected,
            context=context,
        )
        execution_ms = (time.perf_counter() - exec_started) * 1000
        execution = RunbookExecution(
            request_id=request.id,
            runbook_id=request.selected_runbook_id or "",
            status=ITExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
            adapter_name=adapter.name,
            execution_result=result,
        )
        db.add(execution)
        await db.flush()
        await self._add_event(
            db,
            request,
            "request.execution_completed",
            actor.id,
            {"simulated": True, "success": result.get("success")},
        )

        request.status = ITRequestStatus.VALIDATING
        val_started = time.perf_counter()
        validation = self._validate_result(expected, result)
        validation_ms = (time.perf_counter() - val_started) * 1000
        execution.validation_result = validation
        execution.completed_at = datetime.now(UTC)

        if validation["passed"]:
            execution.status = ITExecutionStatus.SUCCESS
            request.status = ITRequestStatus.COMPLETED
            request.completed_at = datetime.now(UTC)
            await self._add_event(db, request, "request.validation_passed", actor.id, {"simulated": True})
            rollback_status = None
            rollback_ms = None
        else:
            execution.status = ITExecutionStatus.FAILED
            request.status = ITRequestStatus.FAILED
            await self._add_event(db, request, "request.validation_failed", actor.id, {"simulated": True})
            rollback_ms, rollback_status = await self._maybe_rollback(
                db, request=request, execution=execution, handler=handler, actor=actor
            )

        db.add(
            ITWorkflowTelemetry(
                request_id=request.id,
                user_id=actor.id,
                planning_latency_ms=planning_ms,
                execution_latency_ms=execution_ms,
                validation_latency_ms=validation_ms,
                rollback_latency_ms=rollback_ms,
                risk_level=request.risk_level.value,
                policy_decision=request.policy_decision.value if request.policy_decision else None,
                approval_required=request.approval_required,
                execution_status=execution.status.value,
                validation_status="passed" if validation["passed"] else "failed",
                rollback_status=rollback_status,
            )
        )

    def _validate_result(self, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
        if not actual.get("simulated"):
            return {"passed": False, "reason": "Non-simulated execution is not permitted in Phase 7"}
        if actual.get("adapter") != "mock":
            return {"passed": False, "reason": "Only the mock execution adapter is enabled"}
        if not actual.get("success"):
            return {"passed": False, "reason": "Simulated execution reported failure"}
        if expected.get("installed") and not actual.get("installed"):
            return {"passed": False, "reason": "Expected simulated installation state was not met"}
        if expected.get("access_granted") and not actual.get("access_granted"):
            return {"passed": False, "reason": "Expected simulated access state was not met"}
        return {"passed": True, "reason": "Simulated result matched the allow-listed plan"}

    async def _maybe_rollback(
        self,
        db: AsyncSession,
        *,
        request: ITRequest,
        execution: RunbookExecution,
        handler,
        actor: User,
    ) -> tuple[float | None, str | None]:
        if not handler.rollback_supported:
            request.status = ITRequestStatus.ESCALATED
            await self._add_event(
                db,
                request,
                "request.escalated",
                actor.id,
                {"reason": "rollback_unsupported"},
            )
            return None, "unsupported"

        await self._add_event(db, request, "request.rollback_started", actor.id, {"simulated": True})
        started = time.perf_counter()
        rollback_result = await get_execution_adapter().rollback(
            runbook_id=execution.runbook_id,
            execution_result=execution.execution_result or {},
        )
        elapsed = (time.perf_counter() - started) * 1000
        if rollback_result.get("rolled_back"):
            execution.status = ITExecutionStatus.ROLLED_BACK
            execution.rollback_status = "completed"
            request.status = ITRequestStatus.ROLLED_BACK
            request.completed_at = datetime.now(UTC)
            await self._add_event(db, request, "request.rollback_completed", actor.id, {"simulated": True})
            return elapsed, "completed"

        request.status = ITRequestStatus.ESCALATED
        execution.rollback_status = "failed"
        await self._add_event(db, request, "request.escalated", actor.id, {"reason": "rollback_failed"})
        return elapsed, "failed"

    async def _load_catalog_matches(self, db: AsyncSession) -> list[CatalogMatch]:
        software = (await db.execute(select(SoftwareCatalog))).scalars().all()
        access = (await db.execute(select(AccessCatalog))).scalars().all()
        matches: list[CatalogMatch] = []
        for item in software:
            matches.append(
                CatalogMatch(
                    kind="software",
                    item_id=str(item.id),
                    name=item.name,
                    runbook_id=item.runbook_id,
                    enabled=item.enabled,
                    risk=item.risk_level.value,
                    approval_required=item.approval_required,
                    aliases=list(item.aliases or []),
                )
            )
        for item in access:
            matches.append(
                CatalogMatch(
                    kind="access",
                    item_id=str(item.id),
                    name=item.resource_name,
                    runbook_id=item.runbook_id,
                    enabled=item.enabled,
                    risk=item.risk_level.value,
                    approval_required=item.approval_required,
                    aliases=list(item.aliases or []),
                )
            )
        return matches

    async def _extraction_from_request(self, db: AsyncSession, request: ITRequest) -> ExtractionResult:
        catalog = await self._load_catalog_matches(db)
        return extract_entities(request.user_message, catalog)

    async def _add_event(
        self,
        db: AsyncSession,
        request: ITRequest,
        event_type: str,
        actor_id: uuid.UUID | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        db.add(
            RequestEvent(
                request_id=request.id,
                event_type=event_type,
                actor_id=actor_id,
                event_metadata=metadata,
            )
        )
        await db.flush()
        await record_audit_event(
            db,
            event_type=f"it.{event_type}",
            user_id=actor_id,
            payload={"request_id": str(request.id)},
        )

    def _ensure_access(self, actor: User, request: ITRequest) -> None:
        if actor.role == UserRole.EMPLOYEE and request.requester_id != actor.id:
            raise ITRequestAccessDeniedError("You do not have access to this IT request")

    def _ensure_can_approve(self, actor: User, request: ITRequest) -> None:
        if actor.id == request.requester_id:
            raise ITRequestAccessDeniedError("You cannot approve your own request")
        if actor.role == UserRole.EMPLOYEE:
            raise ITRequestAccessDeniedError("Employees cannot approve IT requests")
        if actor.role == UserRole.AGENT and request.risk_level in {ITRiskLevel.HIGH, ITRiskLevel.CRITICAL}:
            raise ITRequestAccessDeniedError("Agents cannot approve high or critical requests")
        if actor.role not in {UserRole.AGENT, UserRole.ADMIN}:
            raise ITRequestAccessDeniedError("Insufficient permissions to approve")


_it_request_service: ITRequestService | None = None


def get_it_request_service() -> ITRequestService:
    global _it_request_service
    if _it_request_service is None:
        _it_request_service = ITRequestService()
    return _it_request_service


def reset_it_request_service() -> None:
    global _it_request_service
    _it_request_service = None
