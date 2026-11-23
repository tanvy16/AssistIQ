import type { ReactNode } from "react";

type AlertTone = "error" | "info" | "success";

type AlertProps = {
  children: ReactNode;
  tone?: AlertTone;
};

const toneClasses: Record<AlertTone, string> = {
  error: "border-danger bg-danger-soft text-danger",
  info: "border-surface-border bg-surface-muted text-ink",
  success: "border-accent bg-accent-soft text-ink",
};

export default function Alert({ children, tone = "error" }: AlertProps) {
  return (
    <p className={`rounded border px-3 py-2 text-sm ${toneClasses[tone]}`} role="alert">
      {children}
    </p>
  );
}
