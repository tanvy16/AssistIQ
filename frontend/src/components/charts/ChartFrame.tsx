import { EMPTY_TELEMETRY_MESSAGE } from "../../lib/observabilityMetrics";

export function ChartHeading({ title, unit }: { title: string; unit?: string }) {
  return (
    <div className="mb-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {unit ? <p className="text-xs text-ink-subtle">{unit}</p> : null}
    </div>
  );
}

export function ChartEmpty({
  title = EMPTY_TELEMETRY_MESSAGE,
  description,
}: {
  title?: string;
  description: string;
}) {
  return (
    <div className="flex h-[280px] flex-col justify-center rounded-md border border-dashed border-surface-border bg-canvas px-4">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-lg text-xs leading-5 text-ink-muted">{description}</p>
    </div>
  );
}
