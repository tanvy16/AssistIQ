export type TicketStatus =
  | "open"
  | "in_progress"
  | "pending"
  | "resolved"
  | "closed";

export type TicketPriority = "low" | "medium" | "high" | "critical";

export type TicketCategory =
  | "network"
  | "access"
  | "hardware"
  | "software"
  | "other";

export type UserSummary = {
  id: string;
  email: string;
  display_name: string | null;
};

export type TicketListItem = {
  id: string;
  ticket_number: string;
  title: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  sla_due_at: string;
  created_at: string;
  updated_at: string;
  requester: UserSummary | null;
  assignee: UserSummary | null;
};

export type TicketComment = {
  id: string;
  ticket_id: string;
  author: UserSummary;
  body: string;
  created_at: string;
  updated_at: string;
};

export type TicketEvent = {
  id: string;
  ticket_id: string;
  actor: UserSummary | null;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
};

export type TicketDetail = {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  sla_due_at: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  requester: UserSummary;
  assignee: UserSummary | null;
  comments: TicketComment[];
  events: TicketEvent[];
};

export type TicketListResponse = {
  items: TicketListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type TicketCreateInput = {
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
};

export type TicketFilters = {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
  scope?: "queue" | "assigned";
  page?: number;
  page_size?: number;
};
