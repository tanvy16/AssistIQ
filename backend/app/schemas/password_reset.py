from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.password_reset import (
    PasswordPolicyDecision,
    PasswordResetStatus,
    PasswordRiskLevel,
    PasswordVerificationStatus,
)


class PasswordResetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_user_id: UUID | None = None
    message: str | None = Field(default=None, max_length=2000)


class PasswordResetVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PasswordResetEscalateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=2000)


class PasswordResetEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    actor_id: UUID | None
    event_metadata: dict[str, Any] | None
    created_at: datetime


class PasswordResetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    target_user_id: UUID
    conversation_id: UUID | None
    status: PasswordResetStatus
    verification_status: PasswordVerificationStatus
    risk_level: PasswordRiskLevel
    policy_decision: PasswordPolicyDecision | None
    reason: str | None
    adapter_name: str | None
    execution_result: dict[str, Any] | None
    validation_result: dict[str, Any] | None
    expires_at: datetime
    created_at: datetime
    completed_at: datetime | None
    events: list[PasswordResetEventResponse] = Field(default_factory=list)

    @computed_field
    @property
    def requires_confirmation(self) -> bool:
        return self.status == PasswordResetStatus.CONFIRMATION_REQUIRED


class PasswordResetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    target_user_id: UUID
    status: PasswordResetStatus
    verification_status: PasswordVerificationStatus
    risk_level: PasswordRiskLevel
    policy_decision: PasswordPolicyDecision | None
    created_at: datetime


class PasswordResetListResponse(BaseModel):
    items: list[PasswordResetListItem]
    total: int
