import type {
  EvaluationMetricSet,
  ModelEvaluationRow,
  NamedCount,
  TimePoint,
} from "./observability.types";

export type SeriesPoint = {
  bucket: string;
  label: string;
  value: number;
  count: number;
};

export type MetricBarRow = {
  name: string;
  [metric: string]: string | number;
};

const CLASSIFICATION_KEYS = ["accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc"] as const;
const REGRESSION_KEYS = ["mae", "mse", "rmse", "r2"] as const;
const GENERATION_KEYS = ["groundedness", "faithfulness", "relevance", "citation_correctness"] as const;

export function utcDayKey(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10);
  return date.toISOString().slice(0, 10);
}

export function eachUtcDay(startIso: string, endIso: string): string[] {
  const start = new Date(startIso);
  const end = new Date(endIso);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start > end) {
    return [];
  }
  const days: string[] = [];
  const cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate()));
  const last = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  while (cursor.getTime() <= last.getTime()) {
    days.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return days;
}

export function formatDayLabel(day: string): string {
  const [year, month, date] = day.split("-").map(Number);
  if (!year || !month || !date) return day;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, date)));
}

export function formatBucketTooltip(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

/** Zero-fill missing days for request counts. Does not invent traffic — absent days are 0. */
export function fillDailyCountSeries(
  points: TimePoint[],
  startIso: string,
  endIso: string,
): SeriesPoint[] {
  const byDay = new Map<string, TimePoint>();
  for (const point of points) {
    byDay.set(utcDayKey(point.bucket), point);
  }
  return eachUtcDay(startIso, endIso).map((day) => {
    const point = byDay.get(day);
    const value = point ? Number(point.value ?? point.count ?? 0) : 0;
    return {
      bucket: `${day}T00:00:00.000Z`,
      label: formatDayLabel(day),
      value: Number.isFinite(value) ? value : 0,
      count: point?.count ?? 0,
    };
  });
}

/** Plot only days that have a recorded average. Never fill missing latency with 0. */
export function observedValueSeries(points: TimePoint[]): SeriesPoint[] {
  return points
    .filter((point) => point.value != null && Number.isFinite(point.value) && point.count > 0)
    .map((point) => ({
      bucket: point.bucket,
      label: formatDayLabel(utcDayKey(point.bucket)),
      value: Number(point.value),
      count: point.count,
    }));
}

export function hasUsableTimeSeries(points: { value: number }[]): boolean {
  return points.length >= 2;
}

export function namedCountBars(items: NamedCount[]): { name: string; count: number }[] {
  return items.filter((item) => item.count > 0).map((item) => ({ name: item.name, count: item.count }));
}

function numericMetrics(set: EvaluationMetricSet, keys: readonly string[]): Record<string, number> | null {
  if (set.status !== "evaluated" || !set.metrics) return null;
  const row: Record<string, number> = {};
  for (const key of keys) {
    const value = set.metrics[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      row[key] = value;
    }
  }
  return Object.keys(row).length > 0 ? row : null;
}

export function evaluationChartRows(
  evaluations: ModelEvaluationRow[],
  kind: "classification" | "regression" | "llm_generation",
): { rows: MetricBarRow[]; keys: string[] } {
  const keys =
    kind === "classification" ? CLASSIFICATION_KEYS : kind === "regression" ? REGRESSION_KEYS : GENERATION_KEYS;
  const used = new Set<string>();
  const rows: MetricBarRow[] = [];
  for (const evaluation of evaluations) {
    const metrics = numericMetrics(evaluation[kind], keys);
    if (!metrics) continue;
    Object.keys(metrics).forEach((key) => used.add(key));
    rows.push({ name: evaluation.model_key, ...metrics });
  }
  return { rows, keys: keys.filter((key) => used.has(key)) };
}

export function firstEvaluatedKind(
  evaluations: ModelEvaluationRow[],
): "classification" | "regression" | "llm_generation" | null {
  if (evaluationChartRows(evaluations, "classification").rows.length > 0) return "classification";
  if (evaluationChartRows(evaluations, "regression").rows.length > 0) return "regression";
  if (evaluationChartRows(evaluations, "llm_generation").rows.length > 0) return "llm_generation";
  return null;
}
