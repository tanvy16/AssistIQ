import { useId } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  fillDailyCountSeries,
  formatBucketTooltip,
  hasUsableTimeSeries,
  observedValueSeries,
} from "../../lib/chartSeries";
import { CHART_HEIGHT, useChartColors } from "../../lib/chartTheme";
import { EMPTY_TELEMETRY_MESSAGE } from "../../lib/observabilityMetrics";
import type { TimePoint } from "../../lib/observability.types";
import { ChartEmpty, ChartHeading } from "./ChartFrame";

type TimeSeriesChartProps = {
  title: string;
  unit: string;
  points: TimePoint[];
  color?: string;
  emptyDescription?: string;
  fillMissingDays?: boolean;
  windowStart?: string;
  windowEnd?: string;
  references?: { label: string; value: number; color?: string }[];
};

export default function TimeSeriesChart({
  title,
  unit,
  points,
  color,
  emptyDescription,
  fillMissingDays = false,
  windowStart,
  windowEnd,
  references = [],
}: TimeSeriesChartProps) {
  const colors = useChartColors();
  const gradientId = useId().replace(/:/g, "");
  const stroke = color && !color.startsWith("var(") ? color : colors.accent;
  const series =
    fillMissingDays && windowStart && windowEnd
      ? fillDailyCountSeries(points, windowStart, windowEnd)
      : observedValueSeries(points);
  const usable = hasUsableTimeSeries(series);

  return (
    <div>
      <ChartHeading title={title} unit={unit} />
      {!usable ? (
        <ChartEmpty
          title={EMPTY_TELEMETRY_MESSAGE}
          description={
            emptyDescription ??
            (fillMissingDays
              ? "Daily historical telemetry is unavailable for this window. The backend stores day buckets, so a single-day range cannot be drawn as a time series. Period totals remain in the KPIs."
              : "Not enough recorded samples to plot a series. Aggregates are shown only when the backend reports them.")
          }
        />
      ) : (
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <AreaChart data={series} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: colors.subtle, fontSize: 11 }}
                axisLine={{ stroke: colors.grid }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: colors.subtle, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 6,
                  color: colors.ink,
                  fontSize: 12,
                }}
                labelFormatter={(_, payload) => {
                  const bucket = payload?.[0]?.payload?.bucket as string | undefined;
                  return bucket ? formatBucketTooltip(bucket) : "";
                }}
                formatter={(value) => [`${Number(value)} ${unit}`, title]}
              />
              {references
                .filter((item) => Number.isFinite(item.value))
                .map((item) => (
                  <ReferenceLine
                    key={item.label}
                    y={item.value}
                    stroke={item.color ?? colors.orange}
                    strokeDasharray="4 4"
                    label={{
                      value: item.label,
                      fill: colors.muted,
                      fontSize: 11,
                      position: "insideTopRight",
                    }}
                  />
                ))}
              <Area
                type="monotone"
                dataKey="value"
                stroke={stroke}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={{ r: 3, strokeWidth: 0, fill: stroke }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
