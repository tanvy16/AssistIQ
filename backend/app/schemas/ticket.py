from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: UUID | None = None


class TicketAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: UUID | None = None


class TicketCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=10000)


class UserSummary(BaseModel):
    id: UUID
    email: str
    display_name: str | None

    model_config = {"from_attributes": True}


class TicketListItem(BaseModel):
    id: UUID
    ticket_number: str
    title: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    sla_due_at: datetime
    created_at: datetime
    updated_at: datetime
    requester: UserSummary | None = None
    assignee: UserSummary | None = None

    model_config = {"from_attributes": True}


class TicketCommentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author: UserSummary
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketEventResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    actor: UserSummary | None
    event_type: str
    old_value: str | None
    new_value: str | None
    event_metadata: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: UUID
    ticket_number: str
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    sla_due_at: datetime
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    requester: UserSummary
    assignee: UserSummary | None
    comments: list[TicketCommentResponse] = Field(default_factory=list)
    events: list[TicketEventResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    page_size: int
