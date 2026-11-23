type LoadingStateProps = {
  label?: string;
};

export default function LoadingState({ label = "Loading…" }: LoadingStateProps) {
  return (
    <div
      className="flex items-center py-8"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm text-ink-muted">{label}</p>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`h-3 rounded-sm bg-surface-hover ${className}`}
      aria-hidden="true"
    />
  );
}

export function PanelSkeleton() {
  return (
    <div className="space-y-3 border border-surface-border bg-surface px-4 py-3">
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="h-6 w-1/2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

export function PageFallback() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="status" aria-live="polite">
      <PanelSkeleton />
      <PanelSkeleton />
      <PanelSkeleton />
      <PanelSkeleton />
    </div>
  );
}
