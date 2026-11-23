import { formatSlaLabel, getSlaState, slaStateClasses } from "../../lib/sla";

type SlaBadgeProps = {
  dueAt: string;
};

export default function SlaBadge({ dueAt }: SlaBadgeProps) {
  const state = getSlaState(dueAt);
  const label = formatSlaLabel(dueAt);

  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${slaStateClasses[state]}`}
    >
      {label}
    </span>
  );
}
