from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.ticket import TicketListItem


class TicketStats(BaseModel):
    total: int
    open: int
    in_progress: int
    pending: int
    resolved: int
    closed: int
    assigned_to_me: int
    unassigned_queue: int
    sla_at_risk: int
    sla_breached: int
    sla_compliance_pct: float | None = None


class KnowledgeStats(BaseModel):
    total: int
    published: int
    draft: int
    archived: int


class UserStats(BaseModel):
    total: int
    active: int
    agents: int
    active_agents: int
    employees: int
    admins: int


class AIUsageStats(BaseModel):
    request_count: int
    successful: int
    failed: int
    total_tokens: int | None = None


class ServiceHealth(BaseModel):
    api: str
    database: str


class ActivityItem(BaseModel):
    id: UUID
    ticket_id: UUID
    ticket_number: str
    event_type: str
    actor_name: str | None
    created_at: datetime
    summary: str


class DashboardSummary(BaseModel):
    tickets: TicketStats
    recent_tickets: list[TicketListItem]
    recent_activity: list[ActivityItem]
    health: ServiceHealth
    knowledge: KnowledgeStats | None = None
    users: UserStats | None = None
    ai: AIUsageStats | None = None
