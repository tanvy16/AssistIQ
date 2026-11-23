type RefreshMetaProps = {
  live: boolean;
  updatedAt: Date | null;
  staleReason?: string | null;
};

function formatUpdatedAt(value: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(value);
}

export default function RefreshMeta({ live, updatedAt, staleReason }: RefreshMetaProps) {
  const state = updatedAt == null ? "waiting" : live ? "live" : "stale";
  const badgeClass =
    state === "live"
      ? "border-accent bg-accent-soft text-accent"
      : state === "stale"
        ? "border-storage bg-storage-soft text-storage"
        : "border-surface-border bg-surface-muted text-ink-subtle";
  const dotClass =
    state === "live" ? "bg-accent" : state === "stale" ? "bg-storage" : "bg-ink-subtle";

  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px]">
      <span
        className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-medium uppercase tracking-wide ${badgeClass}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} aria-hidden="true" />
        {state === "live" ? "Live" : state === "stale" ? "Stale" : "Waiting"}
      </span>
      <span className="text-ink-subtle">
        {updatedAt ? `Updated at ${formatUpdatedAt(updatedAt)}` : "Waiting for first refresh"}
      </span>
      {state === "stale" && staleReason ? <span className="text-danger">{staleReason}</span> : null}
    </div>
  );
}
