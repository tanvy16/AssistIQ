export type SlaState = "ok" | "due-soon" | "overdue";

export function getSlaState(dueAtIso: string, now = new Date()): SlaState {
  const due = new Date(dueAtIso);
  if (due.getTime() <= now.getTime()) {
    return "overdue";
  }
  const hoursRemaining = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
  if (hoursRemaining <= 24) {
    return "due-soon";
  }
  return "ok";
}

export function formatSlaLabel(dueAtIso: string, now = new Date()): string {
  const due = new Date(dueAtIso);
  const diffMs = due.getTime() - now.getTime();
  if (diffMs <= 0) {
    return "Overdue";
  }

  const totalMinutes = Math.floor(diffMs / (1000 * 60));
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;

  if (days >= 2) {
    return `Due in ${days} days`;
  }
  if (days === 1) {
    return "Due tomorrow";
  }
  if (hours >= 1) {
    return `Due in ${hours}h ${minutes}m`;
  }
  return `Due in ${minutes}m`;
}

export const slaStateClasses: Record<SlaState, string> = {
  ok: "border-surface-border bg-surface-muted text-ink-subtle",
  "due-soon": "border-storage bg-storage-soft text-storage",
  overdue: "border-danger bg-danger-soft text-danger",
};
