"""Password reset workflow domain models (Phase 8)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PasswordResetStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    VERIFICATION_REQUIRED = "verification_required"
    VERIFICATION_FAILED = "verification_failed"
    RISK_REVIEW = "risk_review"
    CONFIRMATION_REQUIRED = "confirmation_required"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    FAILED = "failed"


class PasswordVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REQUIRES_ESCALATION = "requires_escalation"


class PasswordRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PasswordPolicyDecision(str, enum.Enum):
    ALLOW = "allow"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ESCALATION = "requires_escalation"
    DENY = "deny"


def _enum(enum_cls: type[enum.Enum], name: str, *, create_type: bool = True):
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda values: [value.value for value in values],
        create_type=create_type,
    )


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    escalation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escalations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[PasswordResetStatus] = mapped_column(
        _enum(PasswordResetStatus, "password_reset_status"), index=True
    )
    verification_status: Mapped[PasswordVerificationStatus] = mapped_column(
        _enum(PasswordVerificationStatus, "password_verification_status")
    )
    risk_level: Mapped[PasswordRiskLevel] = mapped_column(
        _enum(PasswordRiskLevel, "password_risk_level")
    )
    policy_decision: Mapped[PasswordPolicyDecision | None] = mapped_column(
        _enum(PasswordPolicyDecision, "password_policy_decision"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_verification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adapter_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["PasswordResetEvent"]] = relationship(back_populates="request")


class PasswordResetEvent(Base):
    __tablename__ = "password_reset_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("password_reset_requests.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    request: Mapped["PasswordResetRequest"] = relationship(back_populates="events")


class PasswordResetTelemetry(Base):
    __tablename__ = "password_reset_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("password_reset_requests.id", ondelete="CASCADE"), index=True
    )
    requester_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    workflow_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    execution_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    iam_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_workflow_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
