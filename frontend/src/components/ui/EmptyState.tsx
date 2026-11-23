import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export default function EmptyState({
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-start rounded-md border border-dashed border-surface-border bg-surface-muted px-4 py-6">
      <h3 className="text-sm font-medium text-ink">{title}</h3>
      <p className="mt-1 max-w-lg text-sm text-ink-muted">{description}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}
