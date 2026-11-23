"""Password reset orchestration: verify → risk → policy → confirm → mock IAM."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.iam.adapter import IAMAdapterError, get_iam_adapter
from app.models.enums import UserRole
from app.models.password_reset import (
    PasswordPolicyDecision,
    PasswordResetEvent,
    PasswordResetRequest,
    PasswordResetStatus,
    PasswordResetTelemetry,
    PasswordRiskLevel,
    PasswordVerificationStatus,
)
from app.models.user import User
from app.services.audit_service import record_audit_event
from app.services.password_reset_policy import PasswordPolicyInput, evaluate_password_reset_policy
from app.services.password_risk import RiskInput, assess_password_reset_risk
from app.services.password_verification import VerificationInput, verify_identity

REQUEST_TTL = timedelta(minutes=30)
SECRET_KEYS = {"password", "token", "secret", "credential", "authorization"}


class PasswordResetError(Exception):
    pass


class PasswordResetNotFoundError(PasswordResetError):
    pass


class PasswordResetAccessDeniedError(PasswordResetError):
    pass


class PasswordResetValidationError(PasswordResetError):
    pass


def _sanitize_metadata(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {key: value for key, value in payload.items() if str(key).lower() not in SECRET_KEYS}


class PasswordResetService:
    async def create_request(
        self,
        db: AsyncSession,
        *,
        actor: User,
        target_user_id: uuid.UUID | None = None,
        message: str | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> PasswordResetRequest:
        target_id = target_user_id or actor.id
        if actor.role == UserRole.EMPLOYEE and target_id != actor.id:
            raise PasswordResetAccessDeniedError("Employees cannot reset another user's password")

        target = await db.get(User, target_id)
        if target is None or not target.is_active:
            raise PasswordResetValidationError("Target user was not found")

        request = PasswordResetRequest(
            requester_id=actor.id,
            target_user_id=target.id,
            conversation_id=conversation_id,
            status=PasswordResetStatus.VERIFICATION_REQUIRED,
            verification_status=PasswordVerificationStatus.PENDING,
            risk_level=PasswordRiskLevel.MEDIUM,
            user_message=message,
            expires_at=datetime.now(UTC) + REQUEST_TTL,
        )
        db.add(request)
        await db.flush()
        await self._add_event(
            db,
            request,
            "password_reset.requested",
            actor.id,
            {"source": "chat" if conversation_id else "api", "self_service": target.id == actor.id},
        )
        await self._telemetry(db, request, "requested", actor=actor)
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def list_requests(self, db: AsyncSession, *, actor: User) -> list[PasswordResetRequest]:
        query = select(PasswordResetRequest).order_by(PasswordResetRequest.created_at.desc())
        if actor.role == UserRole.EMPLOYEE:
            query = query.where(PasswordResetRequest.requester_id == actor.id)
        elif actor.role == UserRole.AGENT:
            query = query.where(
                PasswordResetRequest.status.in_(
                    [
                        PasswordResetStatus.ESCALATED,
                        PasswordResetStatus.VERIFICATION_FAILED,
                        PasswordResetStatus.CONFIRMATION_REQUIRED,
                        PasswordResetStatus.COMPLETED,
                        PasswordResetStatus.REJECTED,
                        PasswordResetStatus.FAILED,
                    ]
                )
            )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_request(
        self, db: AsyncSession, *, actor: User, request_id: uuid.UUID
    ) -> PasswordResetRequest:
        result = await db.execute(
            select(PasswordResetRequest)
            .where(PasswordResetRequest.id == request_id)
            .options(selectinload(PasswordResetRequest.events))
            .execution_options(populate_existing=True)
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise PasswordResetNotFoundError("Password reset request not found")
        self._ensure_access(actor, request)
        return request

    async def verify(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
        email: str,
    ) -> PasswordResetRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        self._ensure_not_expired(request)
        if request.status not in {
            PasswordResetStatus.VERIFICATION_REQUIRED,
            PasswordResetStatus.VERIFICATION_FAILED,
            PasswordResetStatus.SUBMITTED,
        }:
            raise PasswordResetValidationError("Request is not awaiting verification")

        started = time.perf_counter()
        await self._add_event(db, request, "password_reset.verification_started", actor.id, None)
        result = verify_identity(
            VerificationInput(
                actor=actor,
                target_user_id=request.target_user_id,
                submitted_email=email,
                user_message=request.user_message,
            )
        )
        verification_ms = (time.perf_counter() - started) * 1000
        request.verification_status = result.status
        request.reason = result.reason

        if result.status == PasswordVerificationStatus.FAILED:
            request.failed_verification_count += 1
            request.status = PasswordResetStatus.VERIFICATION_FAILED
            await self._add_event(db, request, "password_reset.verification_failed", actor.id, {"reason": result.reason})
            if request.failed_verification_count < 3:
                await self._telemetry(
                    db,
                    request,
                    "verified",
                    actor=actor,
                    verification_latency_ms=verification_ms,
                    verification_result=result.status.value,
                )
                await db.commit()
                return await self.get_request(db, actor=actor, request_id=request.id)
        elif result.status == PasswordVerificationStatus.REQUIRES_ESCALATION:
            request.status = PasswordResetStatus.ESCALATED
            await self._add_event(db, request, "password_reset.verification_failed", actor.id, {"reason": result.reason})
            await self._add_event(db, request, "password_reset.escalated", actor.id, {"reason": result.reason})
        else:
            await self._add_event(db, request, "password_reset.verification_verified", actor.id, None)

        await self._apply_risk_and_policy(db, request=request, actor=actor)
        await self._telemetry(
            db,
            request,
            "verified",
            actor=actor,
            verification_latency_ms=verification_ms,
            verification_result=result.status.value,
        )
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def confirm(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
    ) -> PasswordResetRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        self._ensure_not_expired(request)
        if request.status == PasswordResetStatus.COMPLETED:
            raise PasswordResetValidationError("This password reset has already completed")
        if request.status != PasswordResetStatus.CONFIRMATION_REQUIRED:
            raise PasswordResetValidationError("Request is not awaiting confirmation")
        if request.verification_status != PasswordVerificationStatus.VERIFIED:
            raise PasswordResetValidationError("Identity verification has not succeeded")
        if request.policy_decision != PasswordPolicyDecision.REQUIRES_CONFIRMATION:
            raise PasswordResetValidationError("Policy does not permit confirmation")
        if actor.id != request.requester_id:
            raise PasswordResetAccessDeniedError("Only the requester can confirm this reset")
        if actor.id != request.target_user_id:
            raise PasswordResetAccessDeniedError("You cannot confirm a reset for another user")

        request.status = PasswordResetStatus.APPROVED
        await self._add_event(db, request, "password_reset.confirmed", actor.id, {"simulated": True})
        await self._execute(db, request=request, actor=actor)
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def escalate(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
        reason: str | None = None,
    ) -> PasswordResetRequest:
        request = await self.get_request(db, actor=actor, request_id=request_id)
        terminal = {
            PasswordResetStatus.COMPLETED,
            PasswordResetStatus.REJECTED,
        }
        if request.status in terminal:
            raise PasswordResetValidationError("Completed or rejected requests cannot be escalated")
        request.status = PasswordResetStatus.ESCALATED
        request.reason = reason or "Human review requested"
        await self._add_event(db, request, "password_reset.escalated", actor.id, {"reason": request.reason})
        await self._telemetry(db, request, "escalated", actor=actor, escalated=True)
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def reject(
        self,
        db: AsyncSession,
        *,
        actor: User,
        request_id: uuid.UUID,
        reason: str | None = None,
    ) -> PasswordResetRequest:
        if actor.role not in {UserRole.AGENT, UserRole.ADMIN}:
            raise PasswordResetAccessDeniedError("Only agents or admins can reject reset requests")
        request = await self.get_request(db, actor=actor, request_id=request_id)
        if request.status in {PasswordResetStatus.COMPLETED}:
            raise PasswordResetValidationError("Completed requests cannot be rejected")
        request.status = PasswordResetStatus.REJECTED
        request.completed_at = datetime.now(UTC)
        request.reason = reason or "Rejected by reviewer"
        await self._add_event(db, request, "password_reset.policy_denied", actor.id, {"reason": request.reason})
        await db.commit()
        return await self.get_request(db, actor=actor, request_id=request.id)

    async def _apply_risk_and_policy(
        self, db: AsyncSession, *, request: PasswordResetRequest, actor: User
    ) -> None:
        target = await db.get(User, request.target_user_id)
        if target is None:
            raise PasswordResetValidationError("Target user was not found")

        request.status = PasswordResetStatus.RISK_REVIEW
        risk = assess_password_reset_risk(
            RiskInput(
                requester_id=request.requester_id,
                target_user_id=request.target_user_id,
                requester_role=actor.role,
                target_role=target.role,
                verification_status=request.verification_status,
                failed_verification_count=request.failed_verification_count,
                user_message=request.user_message,
            )
        )
        request.risk_level = risk.risk_level
        await self._add_event(
            db, request, "password_reset.risk_assessed", actor.id, {"risk_level": risk.risk_level.value, "reason": risk.reason}
        )

        started = time.perf_counter()
        policy = evaluate_password_reset_policy(
            PasswordPolicyInput(
                requester_id=request.requester_id,
                target_user_id=request.target_user_id,
                requester_role=actor.role,
                verification_status=request.verification_status,
                risk_level=risk.risk_level,
            )
        )
        policy_ms = (time.perf_counter() - started) * 1000
        request.policy_decision = policy.decision
        request.reason = policy.reason
        await self._telemetry(db, request, "policy", actor=actor, policy_latency_ms=policy_ms)

        if policy.decision == PasswordPolicyDecision.DENY:
            request.status = PasswordResetStatus.REJECTED
            request.completed_at = datetime.now(UTC)
            await self._add_event(db, request, "password_reset.policy_denied", actor.id, {"reason": policy.reason})
        elif policy.decision == PasswordPolicyDecision.REQUIRES_ESCALATION:
            request.status = PasswordResetStatus.ESCALATED
            await self._add_event(db, request, "password_reset.escalated", actor.id, {"reason": policy.reason})
        elif policy.decision == PasswordPolicyDecision.REQUIRES_CONFIRMATION:
            request.status = PasswordResetStatus.CONFIRMATION_REQUIRED
            await self._add_event(db, request, "password_reset.policy_allowed", actor.id, {"next": "confirmation"})
            await self._add_event(db, request, "password_reset.confirmation_required", actor.id, None)
        else:
            # ALLOW is never a pre-confirmation outcome in this policy.
            request.status = PasswordResetStatus.ESCALATED
            await self._add_event(db, request, "password_reset.escalated", actor.id, {"reason": "unexpected_allow"})

    async def _execute(
        self,
        db: AsyncSession,
        *,
        request: PasswordResetRequest,
        actor: User,
    ) -> None:
        if request.verification_status != PasswordVerificationStatus.VERIFIED:
            raise PasswordResetValidationError("Cannot execute without successful verification")
        if request.policy_decision != PasswordPolicyDecision.REQUIRES_CONFIRMATION:
            raise PasswordResetValidationError("Cannot execute unless policy required confirmation")
        if request.status not in {PasswordResetStatus.APPROVED, PasswordResetStatus.EXECUTING}:
            raise PasswordResetValidationError("Request is not approved for execution")

        adapter = get_iam_adapter()
        request.status = PasswordResetStatus.EXECUTING
        request.adapter_name = adapter.name
        await self._add_event(
            db, request, "password_reset.execution_started", actor.id, {"adapter": adapter.name, "simulated": True}
        )

        iam_started = time.perf_counter()
        execution = await adapter.reset_password(
            target_user_id=request.target_user_id,
            request_id=request.id,
            context={},
        )
        iam_ms = (time.perf_counter() - iam_started) * 1000
        request.execution_result = execution
        validation = await adapter.validate_reset(
            target_user_id=request.target_user_id,
            execution_result=execution,
        )
        request.validation_result = validation

        if validation.get("passed"):
            request.status = PasswordResetStatus.COMPLETED
            request.completed_at = datetime.now(UTC)
            await self._add_event(
                db, request, "password_reset.execution_succeeded", actor.id, {"simulated": True, "adapter": adapter.name}
            )
            await self._add_event(
                db, request, "password_reset.completed", actor.id, {"simulated": True, "adapter": adapter.name}
            )
            await self._telemetry(
                db,
                request,
                "completed",
                actor=actor,
                iam_latency_ms=iam_ms,
                execution_result="success",
                success=True,
            )
            return

        request.status = PasswordResetStatus.FAILED
        await self._add_event(
            db, request, "password_reset.execution_failed", actor.id, {"simulated": True, "reason": validation.get("reason")}
        )
        if not adapter.rollback_supported:
            request.status = PasswordResetStatus.ESCALATED
            request.reason = "Simulated reset failed validation and rollback is not supported."
            await self._add_event(
                db, request, "password_reset.escalated", actor.id, {"reason": "validation_failed_rollback_unsupported"}
            )
            await self._telemetry(
                db,
                request,
                "escalated",
                actor=actor,
                iam_latency_ms=iam_ms,
                execution_result="failed",
                success=False,
                escalated=True,
            )
            return

        rollback = await adapter.rollback_reset(
            target_user_id=request.target_user_id, execution_result=execution
        )
        if not rollback.get("rolled_back"):
            request.status = PasswordResetStatus.ESCALATED
            await self._add_event(db, request, "password_reset.escalated", actor.id, {"reason": "rollback_failed"})

    async def _add_event(
        self,
        db: AsyncSession,
        request: PasswordResetRequest,
        event_type: str,
        actor_id: uuid.UUID | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        db.add(
            PasswordResetEvent(
                request_id=request.id,
                event_type=event_type,
                actor_id=actor_id,
                event_metadata=_sanitize_metadata(metadata),
            )
        )
        await db.flush()
        await record_audit_event(
            db,
            event_type=event_type,
            user_id=actor_id,
            payload=_sanitize_metadata(
                {
                    "request_id": str(request.id),
                    "requester_id": str(request.requester_id),
                    "target_user_id": str(request.target_user_id),
                    "risk_level": request.risk_level.value,
                    "policy_decision": request.policy_decision.value if request.policy_decision else None,
                    "adapter": request.adapter_name,
                }
            ),
        )

    async def _telemetry(
        self,
        db: AsyncSession,
        request: PasswordResetRequest,
        stage: str,
        *,
        actor: User,
        verification_latency_ms: float | None = None,
        policy_latency_ms: float | None = None,
        iam_latency_ms: float | None = None,
        verification_result: str | None = None,
        execution_result: str | None = None,
        success: bool | None = None,
        escalated: bool = False,
    ) -> None:
        db.add(
            PasswordResetTelemetry(
                request_id=request.id,
                requester_id=request.requester_id,
                target_user_id=request.target_user_id,
                workflow_stage=stage,
                verification_result=verification_result or request.verification_status.value,
                risk_level=request.risk_level.value,
                policy_decision=request.policy_decision.value if request.policy_decision else None,
                execution_result=execution_result,
                verification_latency_ms=verification_latency_ms,
                policy_latency_ms=policy_latency_ms,
                iam_latency_ms=iam_latency_ms,
                total_workflow_latency_ms=None,
                escalated=escalated or request.status == PasswordResetStatus.ESCALATED,
                success=success,
            )
        )

    def _ensure_access(self, actor: User, request: PasswordResetRequest) -> None:
        if actor.role == UserRole.EMPLOYEE and request.requester_id != actor.id:
            raise PasswordResetAccessDeniedError("You do not have access to this password reset request")

    def _ensure_not_expired(self, request: PasswordResetRequest) -> None:
        if request.status in {
            PasswordResetStatus.REJECTED,
            PasswordResetStatus.FAILED,
        }:
            return
        expires_at = request.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise PasswordResetValidationError("This password reset request has expired")


_service: PasswordResetService | None = None


def get_password_reset_service() -> PasswordResetService:
    global _service
    if _service is None:
        _service = PasswordResetService()
    return _service


def reset_password_reset_service() -> None:
    global _service
    _service = None
