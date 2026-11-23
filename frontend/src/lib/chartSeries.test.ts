import { describe, expect, it } from "vitest";

import {
  eachUtcDay,
  evaluationChartRows,
  fillDailyCountSeries,
  firstEvaluatedKind,
  hasUsableTimeSeries,
  namedCountBars,
  observedValueSeries,
  utcDayKey,
} from "./chartSeries";
import type { ModelEvaluationRow, TimePoint } from "./observability.types";

const unevaluated = {
  status: "Not evaluated" as const,
  metrics: null,
  dataset_ref: null,
  sample_count: null,
  evaluated_at: null,
};

describe("chart series mapping", () => {
  it("fills missing days with zero request counts inside the window", () => {
    const points: TimePoint[] = [
      { bucket: "2026-10-21T00:00:00.000Z", value: 4, count: 4 },
    ];
    const series = fillDailyCountSeries(points, "2026-10-20T00:00:00.000Z", "2026-10-22T12:00:00.000Z");
    expect(series.map((item) => item.value)).toEqual([0, 4, 0]);
    expect(hasUsableTimeSeries(series)).toBe(true);
  });

  it("does not treat a single bucket as a usable time series", () => {
    expect(hasUsableTimeSeries([{ value: 12 }])).toBe(false);
    expect(hasUsableTimeSeries([])).toBe(false);
    expect(eachUtcDay("2026-10-23T08:00:00.000Z", "2026-10-23T20:00:00.000Z")).toEqual(["2026-10-23"]);
  });

  it("keeps only recorded latency averages and never zero-fills them", () => {
    const series = observedValueSeries([
      { bucket: "2026-10-21T00:00:00.000Z", value: 120, count: 3 },
      { bucket: "2026-10-22T00:00:00.000Z", value: null, count: 0 },
      { bucket: "2026-10-23T00:00:00.000Z", value: 90, count: 2 },
    ]);
    expect(series.map((item) => item.value)).toEqual([120, 90]);
    expect(utcDayKey("2026-10-23T18:30:00.000Z")).toBe("2026-10-23");
  });

  it("drops empty named-count bars", () => {
    expect(namedCountBars([{ name: "llm", count: 0 }, { name: "ml", count: 2 }])).toEqual([
      { name: "ml", count: 2 },
    ]);
  });

  it("charts only evaluated numeric metrics and otherwise reports none", () => {
    const evaluations: ModelEvaluationRow[] = [
      {
        model_id: "1",
        model_key: "intent-v1",
        model_name: "intent",
        model_type: "lightweight_ml",
        classification: {
          status: "evaluated",
          metrics: { accuracy: 0.91, f1_score: 0.89 },
          dataset_ref: "ds",
          sample_count: 10,
          evaluated_at: "2026-10-01T00:00:00Z",
        },
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
      {
        model_id: "2",
        model_key: "llama3.2",
        model_name: "llama",
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
        requests: 4,
      },
    ];
    const { rows, keys } = evaluationChartRows(evaluations, "classification");
    expect(keys).toEqual(["accuracy", "f1_score"]);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ name: "intent-v1", accuracy: 0.91, f1_score: 0.89 });
    expect(evaluationChartRows(evaluations, "regression").rows).toEqual([]);
    expect(firstEvaluatedKind(evaluations)).toBe("classification");
    expect(firstEvaluatedKind([evaluations[1]])).toBeNull();
  });
});
