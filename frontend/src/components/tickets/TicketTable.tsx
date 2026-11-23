import { Link } from "react-router-dom";

import TableShell from "../ui/TableShell";
import { formatDateTime } from "../../lib/ticketLabels";
import type { TicketListItem } from "../../lib/tickets.types";
import SlaBadge from "./SlaBadge";
import { TicketCategoryBadge, TicketPriorityBadge, TicketStatusBadge } from "./TicketBadges";

type TicketTableProps = {
  tickets: TicketListItem[];
  detailBasePath: string;
  emptyMessage?: string;
};

export default function TicketTable({
  tickets,
  detailBasePath,
  emptyMessage = "No tickets found.",
}: TicketTableProps) {
  if (tickets.length === 0) {
    return (
      <TableShell
        columns={["Ticket", "Title", "Category", "Priority", "Status", "SLA", "Created"]}
        emptyMessage={emptyMessage}
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-surface-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            {["Ticket", "Title", "Category", "Priority", "Status", "SLA", "Created"].map(
              (column) => (
                <th
                  key={column}
                  scope="col"
                  className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-[0.12em] text-ink-subtle"
                >
                  {column}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody className="bg-surface">
          {tickets.map((ticket) => (
            <tr key={ticket.id} className="border-t border-surface-divider hover:bg-surface-hover">
              <td className="whitespace-nowrap px-3 py-2.5">
                <Link
                  to={`${detailBasePath}/${ticket.id}`}
                  className="ticket-id hover:underline focus-visible:outline-none"
                >
                  {ticket.ticket_number}
                </Link>
              </td>
              <td className="max-w-xs truncate px-3 py-2.5 text-ink">{ticket.title}</td>
              <td className="px-3 py-2.5">
                <TicketCategoryBadge category={ticket.category} />
              </td>
              <td className="px-3 py-2.5">
                <TicketPriorityBadge priority={ticket.priority} />
              </td>
              <td className="px-3 py-2.5">
                <TicketStatusBadge status={ticket.status} />
              </td>
              <td className="px-3 py-2.5">
                <SlaBadge dueAt={ticket.sla_due_at} />
              </td>
              <td className="whitespace-nowrap px-3 py-2.5 text-ink-muted">
                {formatDateTime(ticket.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
