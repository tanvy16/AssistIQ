import type { ReactNode } from "react";

type PanelProps = {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export default function Panel({
  title,
  description,
  children,
  className = "",
}: PanelProps) {
  return (
    <section
      className={`rounded-md border border-surface-border bg-surface ${className}`}
    >
      {title ? (
        <header className="border-b border-surface-divider px-4 py-2.5 sm:px-5">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-xs text-ink-muted">{description}</p>
          ) : null}
        </header>
      ) : null}
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}
