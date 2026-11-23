import {
  categoryBadgeClasses,
  categoryLabels,
  priorityBadgeClasses,
  priorityLabels,
  statusBadgeClasses,
  statusLabels,
} from "../../lib/ticketLabels";
import type { TicketCategory, TicketPriority, TicketStatus } from "../../lib/tickets.types";

type TicketStatusBadgeProps = {
  status: TicketStatus;
};

export function TicketStatusBadge({ status }: TicketStatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${statusBadgeClasses[status]}`}
    >
      {statusLabels[status]}
    </span>
  );
}

type TicketPriorityBadgeProps = {
  priority: TicketPriority;
};

export function TicketPriorityBadge({ priority }: TicketPriorityBadgeProps) {
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${priorityBadgeClasses[priority]}`}
    >
      {priorityLabels[priority]}
    </span>
  );
}

type TicketCategoryBadgeProps = {
  category: TicketCategory;
};

export function TicketCategoryBadge({ category }: TicketCategoryBadgeProps) {
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${categoryBadgeClasses[category]}`}
    >
      {categoryLabels[category]}
    </span>
  );
}
