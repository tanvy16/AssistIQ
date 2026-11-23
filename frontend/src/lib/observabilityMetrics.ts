import { aiModelTypeLabels } from "./aiLabels";
import type { AIModelType } from "./ai.types";
import type {
  EvaluationMetricSet,
  ModelEvaluationRow,
  ModelUsageRow,
  NamedCount,
} from "./observability.types";

export const EMPTY_TELEMETRY_MESSAGE = "No telemetry available for this period.";
export const NOT_EVALUATED_LABEL = "Not evaluated";
export const ESTIMATED_COST_LABEL = "Estimated Cost";
export const MOCK_IT_EXECUTION_LABEL =
  "Execution is currently MOCK/SIMULATED. No real software was installed.";
export const MOCK_IAM_LABEL = "IAM execution is simulated using Mock IAM.";

export const TIME_RANGE_OPTIONS: { key: "24h" | "7d" | "30d"; label: string }[] = [
  { key: "24h", label: "Last 24 hours" },
  { key: "7d", label: "Last 7 days" },
  { key: "30d", label: "Last 30 days" },
];

const SENSITIVE_KEYS = [
  "password",
  "password_hash",
  "jwt",
  "access_token",
  "api_key",
  "secret",
  "iam_credential",
  "shell_command",
];

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatMs(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)} ms`;
}

export function formatCount(value: number | null | undefined): string {
  if (value == null) return "—";
  return String(value);
}

export function formatEstimatedCost(value: number | null | undefined): string {
  if (value == null) return "—";
  return `$${value.toFixed(4)}`;
}

export function formatTokens(value: number | null | undefined, unknownCount = 0): string {
  if (value == null) {
    return unknownCount > 0 ? "Unknown" : "—";
  }
  return value.toLocaleString();
}

export function evaluationDisplay(set: EvaluationMetricSet, metric: string): string {
  if (set.status === "Not evaluated" || !set.metrics || !(metric in set.metrics)) {
    return NOT_EVALUATED_LABEL;
  }
  const value = set.metrics[metric];
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (value == null) return NOT_EVALUATED_LABEL;
  return String(value);
}

export function modelTypeLabel(type: string): string {
  if (type in aiModelTypeLabels) {
    return aiModelTypeLabels[type as AIModelType];
  }
  return type;
}

export function comparisonRows(evaluations: ModelEvaluationRow[], usage: ModelUsageRow[]) {
  const usageByKey = new Map(usage.map((row) => [row.model_key, row]));
  return evaluations.map((row) => {
    const ops = usageByKey.get(row.model_key);
    return {
      model: row.model_key,
      type: modelTypeLabel(row.model_type),
      accuracy: evaluationDisplay(row.classification, "accuracy"),
      f1: evaluationDisplay(row.classification, "f1_score"),
      latency: formatMs(ops?.average_latency_ms ?? row.operational_latency.average_ms),
      requests: ops?.requests ?? row.requests,
    };
  });
}

export function hasChartData(points: NamedCount[] | { count: number }[]): boolean {
  return points.some((point) => point.count > 0);
}

export function containsSensitiveKey(payload: unknown): boolean {
  const text = JSON.stringify(payload).toLowerCase();
  return SENSITIVE_KEYS.some((key) => text.includes(`"${key}"`));
}
