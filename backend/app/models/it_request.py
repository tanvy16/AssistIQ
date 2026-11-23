"""IT request workflow domain models (Phase 7)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ITRequestType(str, enum.Enum):
    SOFTWARE = "software"
    ACCESS = "access"
    PERMISSION = "permission"


class ITRequestStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PARSED = "parsed"
    POLICY_REVIEW = "policy_review"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    PLANNED = "planned"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class ITRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ITApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ITExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ITPolicyDecision(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"
    ESCALATE = "escalate"


class ITCatalogKind(str, enum.Enum):
    SOFTWARE = "software"
    ACCESS = "access"


def _enum(enum_cls: type[enum.Enum], name: str, *, create_type: bool = True):
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda values: [value.value for value in values],
        create_type=create_type,
    )


class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    risk_level: Mapped[ITRiskLevel] = mapped_column(_enum(ITRiskLevel, "it_risk_level"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SoftwareCatalog(Base):
    __tablename__ = "software_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    package_identifier: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    risk_level: Mapped[ITRiskLevel] = mapped_column(
        _enum(ITRiskLevel, "it_risk_level", create_type=False)
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    runbook_id: Mapped[str] = mapped_column(String(128), ForeignKey("runbooks.id", ondelete="RESTRICT"))
    aliases: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AccessCatalog(Base):
    __tablename__ = "access_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="corporate")
    risk_level: Mapped[ITRiskLevel] = mapped_column(
        _enum(ITRiskLevel, "it_risk_level", create_type=False)
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    runbook_id: Mapped[str] = mapped_column(String(128), ForeignKey("runbooks.id", ondelete="RESTRICT"))
    aliases: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ITRequest(Base):
    __tablename__ = "it_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )
    request_type: Mapped[ITRequestType] = mapped_column(_enum(ITRequestType, "it_request_type"))
    status: Mapped[ITRequestStatus] = mapped_column(
        _enum(ITRequestStatus, "it_request_status"), index=True
    )
    requested_resource: Mapped[str] = mapped_column(String(255), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[ITRiskLevel] = mapped_column(
        _enum(ITRiskLevel, "it_risk_level", create_type=False)
    )
    policy_decision: Mapped[ITPolicyDecision | None] = mapped_column(
        _enum(ITPolicyDecision, "it_policy_decision"), nullable=True
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_runbook_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("runbooks.id", ondelete="SET NULL"), nullable=True
    )
    catalog_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entities: Mapped[list["RequestEntity"]] = relationship(back_populates="request")
    approvals: Mapped[list["RequestApproval"]] = relationship(back_populates="request")
    executions: Mapped[list["RunbookExecution"]] = relationship(back_populates="request")
    events: Mapped[list["RequestEvent"]] = relationship(back_populates="request")


class RequestEntity(Base):
    __tablename__ = "request_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("it_requests.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="deterministic")

    request: Mapped["ITRequest"] = relationship(back_populates="entities")


class RequestApproval(Base):
    __tablename__ = "request_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("it_requests.id", ondelete="CASCADE"), index=True
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    status: Mapped[ITApprovalStatus] = mapped_column(
        _enum(ITApprovalStatus, "it_approval_status")
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    request: Mapped["ITRequest"] = relationship(back_populates="approvals")


class RunbookExecution(Base):
    __tablename__ = "runbook_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("it_requests.id", ondelete="CASCADE"), index=True
    )
    runbook_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("runbooks.id", ondelete="RESTRICT")
    )
    status: Mapped[ITExecutionStatus] = mapped_column(
        _enum(ITExecutionStatus, "it_execution_status")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rollback_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    adapter_name: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")

    request: Mapped["ITRequest"] = relationship(back_populates="executions")


class RequestEvent(Base):
    __tablename__ = "request_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("it_requests.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    request: Mapped["ITRequest"] = relationship(back_populates="events")


class ITWorkflowTelemetry(Base):
    __tablename__ = "it_workflow_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("it_requests.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    workflow_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    planning_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rollback_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execution_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rollback_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
