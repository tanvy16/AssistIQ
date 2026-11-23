import type { ReactNode } from "react";

export type BadgeVariant =
  | "default"
  | "accent"
  | "muted"
  | "ai"
  | "success"
  | "danger"
  | "warning"
  | "network"
  | "activity";

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
};

const variantClasses: Record<BadgeVariant, string> = {
  default: "border-surface-border bg-surface-muted text-ink",
  accent: "border-accent bg-accent-soft text-accent",
  muted: "border-surface-border bg-surface-muted text-ink-subtle",
  ai: "border-ai bg-ai-soft text-ai",
  success: "border-accent bg-accent-soft text-accent",
  danger: "border-danger bg-danger-soft text-danger",
  warning: "border-storage bg-storage-soft text-storage",
  network: "border-network bg-network-soft text-network",
  activity: "border-activity bg-activity-soft text-activity",
};

export default function Badge({ children, variant = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${variantClasses[variant]}`}
    >
      {children}
    </span>
  );
}
