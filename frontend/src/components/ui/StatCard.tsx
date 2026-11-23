import type { ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "warning" | "danger" | "success" | "network" | "ai" | "activity";
};

const toneClasses: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "stat-card",
  warning: "stat-card stat-card-warning",
  danger: "stat-card stat-card-danger",
  success: "stat-card stat-card-success",
  network: "stat-card stat-card-network",
  ai: "stat-card stat-card-ai",
  activity: "stat-card stat-card-activity",
};

export default function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  return (
    <section className={`px-4 py-3 ${toneClasses[tone]}`}>
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-subtle">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-1 text-xs text-ink-muted">{hint}</p> : null}
    </section>
  );
}
