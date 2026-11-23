from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_id: UUID
    title: str
    similarity_score: float
    category: str | None = None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model_id: UUID | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    intent: str | None = None
    confidence_state: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    status: str
    selected_model_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    selected_model_id: UUID | None = None


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=8000)
    selected_model_id: UUID | None = None


class SendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class EscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=128)
    notes: str | None = Field(default=None, max_length=2000)


class EscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    requested_by: UUID
    reason: str
    status: str
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None
    ticket_id: UUID | None = None
    ticket_number: str | None = None
