import type { TicketStats } from "../../lib/dashboard.types";
import { useChartColors } from "../../lib/chartTheme";

type StatusMixProps = {
  tickets: TicketStats | undefined;
};

export default function StatusMix({ tickets }: StatusMixProps) {
  const colors = useChartColors();
  const total = tickets?.total ?? 0;
  const segments: { key: keyof TicketStats; label: string; color: string }[] = [
    { key: "open", label: "Open", color: colors.teal },
    { key: "in_progress", label: "In progress", color: colors.violet },
    { key: "pending", label: "Pending", color: colors.yellow },
    { key: "resolved", label: "Resolved", color: colors.accent },
    { key: "closed", label: "Closed", color: colors.grid },
  ];
  return (
    <div>
      <h3 className="text-sm font-semibold text-ink">Ticket status mix</h3>
      <p className="text-xs text-ink-subtle">Counts from the current dashboard summary</p>
      {tickets == null ? (
        <p className="mt-3 text-sm text-ink-muted">Waiting for ticket totals…</p>
      ) : total === 0 ? (
        <p className="mt-3 text-sm text-ink-muted">No tickets are in this workspace yet.</p>
      ) : (
        <>
          <div className="mt-3 flex h-2 overflow-hidden rounded-sm bg-surface-hover">
            {segments.map((segment) => {
              const value = Number(tickets?.[segment.key] ?? 0);
              if (value <= 0) return null;
              return (
                <div
                  key={segment.key}
                  style={{ width: `${(value / total) * 100}%`, backgroundColor: segment.color }}
                  title={`${segment.label}: ${value}`}
                />
              );
            })}
          </div>
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
            {segments.map((segment) => (
              <li key={segment.key} className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-sm" style={{ backgroundColor: segment.color }} />
                {segment.label} {Number(tickets?.[segment.key] ?? 0)}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
