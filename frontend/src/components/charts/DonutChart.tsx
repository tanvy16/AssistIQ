import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { ChartSegment } from "../../lib/chartGeometry";
import { useChartColors } from "../../lib/chartTheme";
import { EMPTY_TELEMETRY_MESSAGE } from "../../lib/observabilityMetrics";
import { ChartEmpty, ChartHeading } from "./ChartFrame";

type DonutChartProps = {
  title: string;
  unit: string;
  items: ChartSegment[];
  emptyDescription?: string;
  centerLabel?: string;
};

const TOKEN_TO_KEY: Record<string, keyof ReturnType<typeof useChartColors>> = {
  "var(--color-accent)": "accent",
  "var(--color-network)": "teal",
  "var(--color-ai)": "violet",
  "var(--color-activity)": "orange",
  "var(--color-storage)": "yellow",
  "var(--color-danger)": "coral",
  "var(--color-ink-subtle)": "subtle",
};

/** Theme-aware semantic colour for a CSS token; undefined -> palette fallback. */
function resolveToken(color: string | undefined, colors: ReturnType<typeof useChartColors>): string | undefined {
  if (!color) return undefined;
  const key = TOKEN_TO_KEY[color];
  if (key) return colors[key] as string;
  return color.startsWith("var(") ? undefined : color;
}

export default function DonutChart({
  title,
  unit,
  items,
  emptyDescription = "No values were recorded for this period.",
  centerLabel = "total",
}: DonutChartProps) {
  const colors = useChartColors();
  const total = items.reduce((sum, item) => sum + Math.max(item.value, 0), 0);
  const slices = items
    .map((item, index) => ({
      ...item,
      color: resolveToken(item.color, colors) ?? colors.series[index % colors.series.length],
    }))
    .filter((item) => item.value > 0);

  return (
    <div>
      <ChartHeading title={title} unit={unit} />
      {total <= 0 ? (
        <ChartEmpty title={EMPTY_TELEMETRY_MESSAGE} description={emptyDescription} />
      ) : (
        <div className="flex flex-col items-stretch gap-4 sm:flex-row sm:items-center">
          <div className="relative mx-auto h-[240px] w-[240px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={slices}
                  dataKey="value"
                  nameKey="label"
                  innerRadius={68}
                  outerRadius={96}
                  paddingAngle={slices.length > 1 ? 2 : 0}
                  stroke={colors.tooltipBg}
                  strokeWidth={2}
                  isAnimationActive={false}
                >
                  {slices.map((slice) => (
                    <Cell key={slice.label} fill={slice.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: colors.tooltipBg,
                    border: `1px solid ${colors.border}`,
                    borderRadius: 6,
                    color: colors.ink,
                    fontSize: 12,
                  }}
                  formatter={(value, name) => [`${Number(value)} ${unit}`, String(name)]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <p className="text-2xl font-semibold tabular-nums text-ink">{total}</p>
              <p className="text-[11px] uppercase tracking-[0.12em] text-ink-subtle">{centerLabel}</p>
            </div>
          </div>
          <ul className="min-w-[10rem] space-y-2 text-sm">
            {items.map((item) => (
              <li key={item.label} className="flex items-center justify-between gap-3 text-ink-muted">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-sm"
                    style={{
                      // Same resolution as the ring, so legend and slices always agree.
                      backgroundColor:
                        resolveToken(item.color, colors) ??
                        colors.series[items.indexOf(item) % colors.series.length],
                    }}
                  />
                  {item.label}
                </span>
                <span className="font-medium tabular-nums text-ink">{item.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
