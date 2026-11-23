import type {
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from "./tickets.types";

export const statusLabels: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  pending: "Pending",
  resolved: "Resolved",
  closed: "Closed",
};

export const priorityLabels: Record<TicketPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const categoryLabels: Record<TicketCategory, string> = {
  network: "Network",
  access: "Access",
  hardware: "Hardware",
  software: "Software",
  other: "Other",
};

export const statusBadgeClasses: Record<TicketStatus, string> = {
  open: "border-network bg-network-soft text-network",
  in_progress: "border-ai bg-ai-soft text-ai",
  pending: "border-activity bg-activity-soft text-activity",
  resolved: "border-accent bg-accent-soft text-accent",
  closed: "border-surface-border bg-surface-muted text-ink-subtle",
};

export const priorityBadgeClasses: Record<TicketPriority, string> = {
  low: "border-surface-border bg-surface-muted text-ink-subtle",
  medium: "border-surface-border bg-surface text-ink-muted",
  high: "border-storage bg-storage-soft text-storage",
  critical: "border-danger bg-danger-soft text-danger",
};

export const categoryBadgeClasses: Record<TicketCategory, string> = {
  network: "border-network bg-network-soft text-network",
  access: "border-ai bg-ai-soft text-ai",
  hardware: "border-storage bg-storage-soft text-storage",
  software: "border-activity bg-activity-soft text-activity",
  other: "border-surface-border bg-surface-muted text-ink-subtle",
};

export function formatEventLabel(eventType: string): string {
  return eventType.replace("ticket.", "").replace(/_/g, " ");
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
