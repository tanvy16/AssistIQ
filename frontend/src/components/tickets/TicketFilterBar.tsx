import { priorityLabels, statusLabels } from "../../lib/ticketLabels";
import type { TicketPriority, TicketStatus } from "../../lib/tickets.types";
import type { SlaState } from "../../lib/sla";

type TicketFilterBarProps = {
  status: TicketStatus | "";
  priority: TicketPriority | "";
  sla: SlaState | "";
  onStatusChange: (value: TicketStatus | "") => void;
  onPriorityChange: (value: TicketPriority | "") => void;
  onSlaChange: (value: SlaState | "") => void;
};

export default function TicketFilterBar({
  status,
  priority,
  sla,
  onStatusChange,
  onPriorityChange,
  onSlaChange,
}: TicketFilterBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-sm text-ink-muted">
        Status
        <select
          className="field-control mt-1 w-auto min-w-[10rem]"
          value={status}
          onChange={(event) => onStatusChange(event.target.value as TicketStatus | "")}
        >
          <option value="">All statuses</option>
          {(Object.keys(statusLabels) as TicketStatus[]).map((value) => (
            <option key={value} value={value}>
              {statusLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm text-ink-muted">
        Priority
        <select
          className="field-control mt-1 w-auto min-w-[10rem]"
          value={priority}
          onChange={(event) => onPriorityChange(event.target.value as TicketPriority | "")}
        >
          <option value="">All priorities</option>
          {(Object.keys(priorityLabels) as TicketPriority[]).map((value) => (
            <option key={value} value={value}>
              {priorityLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm text-ink-muted">
        SLA
        <select
          className="field-control mt-1 w-auto min-w-[10rem]"
          value={sla}
          onChange={(event) => onSlaChange(event.target.value as SlaState | "")}
        >
          <option value="">All SLA states</option>
          <option value="overdue">Overdue</option>
          <option value="due-soon">Due soon</option>
          <option value="ok">On time</option>
        </select>
      </label>
      <p className="pb-2 text-[11px] text-ink-subtle">SLA filters the currently loaded page.</p>
    </div>
  );
}
