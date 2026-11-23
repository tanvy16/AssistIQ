from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import KnowledgeDocumentStatus, TicketCategory


class KnowledgeDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    body: str = Field(default="", max_length=100000)
    category: TicketCategory
    source: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] | None = None


class KnowledgeDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    body: str | None = Field(default=None, max_length=100000)
    category: TicketCategory | None = None
    source: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] | None = None


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    description: str | None
    body: str
    category: TicketCategory
    source: str | None
    status: KnowledgeDocumentStatus
    version: int
    created_by: UUID
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="doc_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]
    total: int


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty")
        return stripped


class KnowledgeSearchResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    content: str
    similarity_score: float
    category: str
    source: str | None
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]
    total: int
