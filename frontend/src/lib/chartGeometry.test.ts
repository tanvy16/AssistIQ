import { describe, expect, it } from "vitest";

import { barPercents, donutSegments, seriesPath } from "./chartGeometry";

describe("chart geometry", () => {
  it("builds donut arcs from real totals and ignores empty series", () => {
    expect(donutSegments([{ label: "ok", value: 0, color: "green" }])).toEqual([]);
    const segments = donutSegments([
      { label: "success", value: 3, color: "green" },
      { label: "failed", value: 1, color: "coral" },
    ]);
    expect(segments).toHaveLength(2);
    expect(segments[0].d.startsWith("M ")).toBe(true);
    expect(segments[0].endAngle).toBe(270);
    expect(segments[1].endAngle).toBe(360);
  });

  it("scales time-series paths from actual values", () => {
    expect(seriesPath([])).toBe("");
    const path = seriesPath([0, 10, 5], 100, 36, 2);
    expect(path.startsWith("M")).toBe(true);
    expect(path).toContain(" L");
  });

  it("computes bar widths without fabricating a maximum", () => {
    expect(barPercents([0, 0])).toEqual([0, 0]);
    expect(barPercents([2, 4])).toEqual([50, 100]);
  });
});
