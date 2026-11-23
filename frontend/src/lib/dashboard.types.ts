import type { TicketListItem } from "./tickets.types";

export type TicketStats = {
  total: number;
  open: number;
  in_progress: number;
  pending: number;
  resolved: number;
  closed: number;
  assigned_to_me: number;
  unassigned_queue: number;
  sla_at_risk: number;
  sla_breached: number;
  sla_compliance_pct: number | null;
};

export type KnowledgeStats = {
  total: number;
  published: number;
  draft: number;
  archived: number;
};

export type UserStats = {
  total: number;
  active: number;
  agents: number;
  active_agents: number;
  employees: number;
  admins: number;
};

export type AIUsageStats = {
  request_count: number;
  successful: number;
  failed: number;
  total_tokens: number | null;
};

export type ServiceHealth = {
  api: string;
  database: string;
};

export type ActivityItem = {
  id: string;
  ticket_id: string;
  ticket_number: string;
  event_type: string;
  actor_name: string | null;
  created_at: string;
  summary: string;
};

export type DashboardSummary = {
  tickets: TicketStats;
  recent_tickets: TicketListItem[];
  recent_activity: ActivityItem[];
  health: ServiceHealth;
  knowledge: KnowledgeStats | null;
  users: UserStats | null;
  ai: AIUsageStats | null;
};
