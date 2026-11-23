from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.it_request import (
    ITPolicyDecision,
    ITRequestStatus,
    ITRequestType,
    ITRiskLevel,
)


class ITRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=4000)
    request_type: ITRequestType | None = None


class RequestEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_name: str
    entity_value: str
    confidence: float
    source: str


class RequestEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    actor_id: UUID | None
    event_metadata: dict[str, Any] | None
    created_at: datetime


class RequestApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    approver_id: UUID
    status: str
    decision: str
    comment: str | None
    decided_at: datetime


class RunbookExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    runbook_id: str
    status: str
    adapter_name: str
    started_at: datetime | None
    completed_at: datetime | None
    execution_result: dict[str, Any] | None
    validation_result: dict[str, Any] | None
    rollback_status: str | None


class ITRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    conversation_id: UUID | None
    ticket_id: UUID | None
    request_type: ITRequestType
    status: ITRequestStatus
    requested_resource: str
    justification: str | None
    risk_level: ITRiskLevel
    policy_decision: ITPolicyDecision | None
    approval_required: bool
    selected_runbook_id: str | None
    extraction_confidence: float | None
    user_message: str
    plan: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    entities: list[RequestEntityResponse] = Field(default_factory=list)
    approvals: list[RequestApprovalResponse] = Field(default_factory=list)
    executions: list[RunbookExecutionResponse] = Field(default_factory=list)


class ITRequestListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_type: ITRequestType
    status: ITRequestStatus
    requested_resource: str
    risk_level: ITRiskLevel
    policy_decision: ITPolicyDecision | None
    approval_required: bool
    created_at: datetime


class ITRequestListResponse(BaseModel):
    items: list[ITRequestListItem]
    total: int


class ApprovalActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str | None = Field(default=None, max_length=2000)


class SoftwareCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    vendor: str | None
    version: str | None
    package_identifier: str
    risk_level: ITRiskLevel
    approval_required: bool
    enabled: bool
    runbook_id: str
    aliases: list[str] | None


class AccessCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_name: str
    resource_type: str
    environment: str
    risk_level: ITRiskLevel
    approval_required: bool
    enabled: bool
    runbook_id: str
    aliases: list[str] | None


class RunbookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    action_type: str
    enabled: bool
    risk_level: ITRiskLevel
    description: str | None
    rollback_supported: bool


class CatalogEnableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
