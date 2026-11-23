import { afterEach, describe, expect, it, vi } from "vitest";

import { buildObservabilityQuery, fetchObservabilityDashboard } from "./observability";
import type { EvaluationMetricSet, ModelEvaluationRow } from "./observability.types";
import {
  EMPTY_TELEMETRY_MESSAGE,
  ESTIMATED_COST_LABEL,
  MOCK_IAM_LABEL,
  MOCK_IT_EXECUTION_LABEL,
  NOT_EVALUATED_LABEL,
  TIME_RANGE_OPTIONS,
  comparisonRows,
  containsSensitiveKey,
  evaluationDisplay,
  formatEstimatedCost,
  formatMs,
  formatPercent,
  formatTokens,
  hasChartData,
} from "./observabilityMetrics";

const unevaluated: EvaluationMetricSet = {
  status: "Not evaluated",
  metrics: null,
  dataset_ref: null,
  sample_count: null,
  evaluated_at: null,
};

describe("observability query builder", () => {
  it("encodes preset ranges", () => {
    expect(buildObservabilityQuery("24h")).toBe("range=24h");
    expect(buildObservabilityQuery("7d")).toBe("range=7d");
    expect(buildObservabilityQuery("30d")).toBe("range=30d");
  });

  it("converts custom dates to ISO query params", () => {
    const query = buildObservabilityQuery(
      "custom",
      "2015-06-01T00:00:00.000Z",
      "2015-06-02T00:00:00.000Z",
    );
    const params = new URLSearchParams(query);
    expect(params.get("range")).toBe("custom");
    expect(params.get("start")).toContain("2015-06-01");
    expect(params.get("end")).toContain("2015-06-02");
  });
});

describe("observability metric labels", () => {
  it("uses honest empty and unevaluated labels", () => {
    expect(EMPTY_TELEMETRY_MESSAGE).toBe("No telemetry available for this period.");
    expect(NOT_EVALUATED_LABEL).toBe("Not evaluated");
    expect(ESTIMATED_COST_LABEL).toBe("Estimated Cost");
    expect(MOCK_IT_EXECUTION_LABEL).toMatch(/MOCK|SIMULATED/);
    expect(MOCK_IAM_LABEL).toMatch(/Mock IAM/);
  });

  it("formats null metrics without inventing values", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatMs(null)).toBe("—");
    expect(formatEstimatedCost(null)).toBe("—");
    expect(formatTokens(null, 3)).toBe("Unknown");
    expect(formatTokens(null, 0)).toBe("—");
    expect(formatPercent(0.5)).toBe("50.0%");
    expect(formatEstimatedCost(0.0015)).toBe("$0.0015");
  });

  it("returns Not evaluated when ground truth is missing", () => {
    expect(evaluationDisplay(unevaluated, "accuracy")).toBe("Not evaluated");
    expect(
      evaluationDisplay(
        {
          status: "evaluated",
          metrics: { accuracy: 0.91 },
          dataset_ref: "intent-eval-v1",
          sample_count: 10,
          evaluated_at: "2015-06-01T00:00:00Z",
        },
        "f1_score",
      ),
    ).toBe("Not evaluated");
    expect(
      evaluationDisplay(
        {
          status: "evaluated",
          metrics: { accuracy: 0.91 },
          dataset_ref: "intent-eval-v1",
          sample_count: 10,
          evaluated_at: "2015-06-01T00:00:00Z",
        },
        "accuracy",
      ),
    ).toBe("0.910");
  });

  it("builds model comparison rows from evaluation + usage", () => {
    const evaluations: ModelEvaluationRow[] = [
      {
        model_id: "1",
        model_key: "test-ml-v1",
        model_name: "logreg-test",
        model_type: "lightweight_ml",
        classification: {
          status: "evaluated",
          metrics: { accuracy: 0.91, f1_score: 0.89 },
          dataset_ref: "ds",
          sample_count: 10,
          evaluated_at: "2015-06-01T00:00:00Z",
        },
        regression: unevaluated,
        llm_generation: unevaluated,
        operational_latency: {
          count: 4,
          average_ms: 20,
          min_ms: 10,
          max_ms: 40,
          p50_ms: 20,
          p95_ms: 38,
          p99_ms: 40,
        },
        requests: 4,
      },
      {
        model_id: "2",
        model_key: "test-llm-v1",
        model_name: "gpt-4o-mini",
        model_type: "llm",
        classification: unevaluated,
        regression: unevaluated,
        llm_generation: unevaluated,
        operational_latency: {
          count: 0,
          average_ms: null,
          min_ms: null,
          max_ms: null,
          p50_ms: null,
          p95_ms: null,
          p99_ms: null,
        },
        requests: 0,
      },
    ];
    const rows = comparisonRows(evaluations, [
      {
        model_key: "test-ml-v1",
        model_name: "logreg-test",
        model_type: "lightweight_ml",
        provider: "local",
        requests: 4,
        successful: 4,
        failed: 0,
        success_rate: 1,
        average_latency_ms: 20,
        p95_latency_ms: 38,
        prompt_tokens: null,
        completion_tokens: null,
        total_tokens: null,
        tokens_unknown_requests: 4,
        estimated_cost_usd: null,
        cost_unknown_requests: 4,
        inference_units: 4,
      },
    ]);
    expect(rows[0]).toMatchObject({
      model: "test-ml-v1",
      type: "Lightweight ML",
      accuracy: "0.910",
      f1: "0.890",
      requests: 4,
    });
    expect(rows[1].accuracy).toBe("Not evaluated");
    expect(rows[1].f1).toBe("Not evaluated");
    expect(rows[1].type).toBe("LLM");
  });

  it("hides empty charts", () => {
    expect(hasChartData([])).toBe(false);
    expect(hasChartData([{ name: "llm", count: 0 }])).toBe(false);
    expect(hasChartData([{ name: "llm", count: 3 }])).toBe(true);
  });

  it("exposes the four time-range options used by the dashboard", () => {
    expect(TIME_RANGE_OPTIONS.map((item) => item.key)).toEqual(["24h", "7d", "30d"]);
  });

  it("does not treat aggregated payloads as containing secrets", () => {
    expect(
      containsSensitiveKey({
        total_ai_requests: 0,
        estimated_cost_usd: null,
        execution_mode: MOCK_IAM_LABEL,
      }),
    ).toBe(false);
    expect(containsSensitiveKey({ password_hash: "x" })).toBe(true);
  });
});

describe("observability API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps dashboard endpoints into a single payload", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(url);
        const path = url.split("/observability/")[1]?.split("?")[0];
        const payload =
          path === "summary"
            ? {
                window: { range: "7d", start: "", end: "" },
                total_ai_requests: 0,
                success_rate: null,
                average_latency_ms: null,
                p95_latency_ms: null,
                total_llm_tokens: null,
                estimated_cost_usd: null,
                cost_label: "Estimated Cost",
                escalation_rate: null,
                empty: true,
              }
            : path === "models" || path === "evaluations" || path === "anomalies"
              ? { items: [] }
              : path === "tokens"
                ? {
                    prompt_tokens: null,
                    completion_tokens: null,
                    total_tokens: null,
                    requests_with_usage: 0,
                    requests_without_usage: 0,
                    average_tokens_per_request: null,
                    by_model: [],
                    by_task: [],
                    over_time: [],
                  }
                : path === "cost"
                  ? {
                      label: "Estimated Cost",
                      total_estimated_usd: null,
                      requests_with_cost: 0,
                      requests_without_cost: 0,
                      average_cost_per_request: null,
                      by_model: [],
                      by_task: [],
                      over_time: [],
                    }
                  : path === "usage"
                    ? {
                        counts: { total: 0, successful: 0, failed: 0, success_rate: null },
                        by_model_type: [],
                        by_provider: [],
                        by_task: [],
                        over_time: [],
                      }
                    : path === "latency"
                      ? {
                          overall: {
                            count: 0,
                            average_ms: null,
                            min_ms: null,
                            max_ms: null,
                            p50_ms: null,
                            p95_ms: null,
                            p99_ms: null,
                          },
                          by_model: [],
                          over_time: [],
                        }
                      : path === "rag"
                        ? {
                            retrieval: { precision_at_k: "Not evaluated" },
                            generation: { groundedness: "Not evaluated" },
                            notes: "",
                          }
                        : path === "chat"
                          ? {
                              conversations: 0,
                              messages: 0,
                              latency: {
                                count: 0,
                                average_ms: null,
                                min_ms: null,
                                max_ms: null,
                                p50_ms: null,
                                p95_ms: null,
                                p99_ms: null,
                              },
                              retrieval_latency: {
                                count: 0,
                                average_ms: null,
                                min_ms: null,
                                max_ms: null,
                                p50_ms: null,
                                p95_ms: null,
                                p99_ms: null,
                              },
                              generation_latency: {
                                count: 0,
                                average_ms: null,
                                min_ms: null,
                                max_ms: null,
                                p50_ms: null,
                                p95_ms: null,
                                p99_ms: null,
                              },
                              average_retrieved_chunks: null,
                              average_similarity: null,
                              citation_rate: null,
                              average_citations: null,
                              escalation_rate: null,
                              escalations: 0,
                              confidence: [],
                              intents: [],
                              unsupported_rate: null,
                            }
                          : path === "it-workflows"
                            ? {
                                total_requests: 0,
                                by_type: [],
                                by_status: [],
                                by_risk: [],
                                by_policy: [],
                                policy_allow_rate: null,
                                approval_required_rate: null,
                                denial_rate: null,
                                escalation_rate: null,
                                execution_success_rate: null,
                                validation_success_rate: null,
                                rollback_rate: null,
                                stage_latency: {},
                                execution_mode: MOCK_IT_EXECUTION_LABEL,
                              }
                            : {
                                total_requests: 0,
                                by_status: [],
                                by_risk: [],
                                by_policy: [],
                                verification_success_rate: null,
                                verification_failure_rate: null,
                                confirmation_rate: null,
                                completion_rate: null,
                                failure_rate: null,
                                escalation_rate: null,
                                stage_latency: {},
                                execution_mode: MOCK_IAM_LABEL,
                              };
        return {
          ok: true,
          json: async () => payload,
        };
      }),
    );

    const dashboard = await fetchObservabilityDashboard("token", "7d");
    expect(dashboard.summary.empty).toBe(true);
    expect(dashboard.summary.cost_label).toBe("Estimated Cost");
    expect(dashboard.models).toEqual([]);
    expect(dashboard.evaluations).toEqual([]);
    expect(dashboard.anomalies).toEqual([]);
    expect(dashboard.rag.generation.groundedness).toBe("Not evaluated");
    expect(dashboard.itWorkflows.execution_mode).toMatch(/MOCK|SIMULATED/);
    expect(dashboard.passwordResets.execution_mode).toMatch(/Mock IAM/);
    expect(calls.some((url) => url.includes("/api/v1/observability/summary?range=7d"))).toBe(true);
  });
});
