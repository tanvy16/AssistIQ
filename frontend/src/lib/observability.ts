import { API_BASE_URL, authFetch } from "./api";
import type {
  Anomaly,
  CostSummary,
  LatencyBreakdown,
  ModelEvaluationRow,
  ModelUsageRow,
  ObservabilityDashboard,
  ObservabilitySummary,
  PasswordResetObservability,
  RagObservability,
  TimeRangeKey,
  TokenSummary,
  UsageBreakdown,
  ChatObservability,
  WorkflowObservability,
} from "./observability.types";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

function toIso(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toISOString();
}

export function buildObservabilityQuery(
  range: TimeRangeKey,
  customStart?: string,
  customEnd?: string,
): string {
  const params = new URLSearchParams({ range });
  if (range === "custom" && customStart && customEnd) {
    params.set("start", toIso(customStart));
    params.set("end", toIso(customEnd));
  }
  return params.toString();
}

async function getJson<T>(
  accessToken: string,
  path: string,
  query: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/observability/${path}?${query}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchObservabilityDashboard(
  accessToken: string,
  range: TimeRangeKey,
  customStart?: string,
  customEnd?: string,
  signal?: AbortSignal,
): Promise<ObservabilityDashboard> {
  const query = buildObservabilityQuery(range, customStart, customEnd);
  const [
    summary,
    models,
    usage,
    tokens,
    cost,
    latency,
    rag,
    chat,
    itWorkflows,
    passwordResets,
    evaluations,
    anomalies,
  ] = await Promise.all([
    getJson<ObservabilitySummary>(accessToken, "summary", query, signal),
    getJson<{ items: ModelUsageRow[] }>(accessToken, "models", query, signal),
    getJson<UsageBreakdown>(accessToken, "usage", query, signal),
    getJson<TokenSummary>(accessToken, "tokens", query, signal),
    getJson<CostSummary>(accessToken, "cost", query, signal),
    getJson<LatencyBreakdown>(accessToken, "latency", query, signal),
    getJson<RagObservability>(accessToken, "rag", query, signal),
    getJson<ChatObservability>(accessToken, "chat", query, signal),
    getJson<WorkflowObservability>(accessToken, "it-workflows", query, signal),
    getJson<PasswordResetObservability>(accessToken, "password-resets", query, signal),
    getJson<{ items: ModelEvaluationRow[] }>(accessToken, "evaluations", query, signal),
    getJson<{ items: Anomaly[] }>(accessToken, "anomalies", query, signal),
  ]);

  return {
    summary,
    models: models.items,
    usage,
    tokens,
    cost,
    latency,
    rag,
    chat,
    itWorkflows,
    passwordResets,
    evaluations: evaluations.items,
    anomalies: anomalies.items,
  };
}
