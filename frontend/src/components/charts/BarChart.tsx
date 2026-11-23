import { Bar, BarChart as ReBarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { namedCountBars } from "../../lib/chartSeries";
import { useChartColors } from "../../lib/chartTheme";
import { EMPTY_TELEMETRY_MESSAGE } from "../../lib/observabilityMetrics";
import type { NamedCount } from "../../lib/observability.types";
import { ChartEmpty, ChartHeading } from "./ChartFrame";

type BarChartProps = {
  title: string;
  unit: string;
  items: NamedCount[];
  color?: string;
  emptyDescription?: string;
  includeZeros?: boolean;
};

function resolveColor(color: string | undefined, fallback: string, colors: ReturnType<typeof useChartColors>): string {
  if (!color) return fallback;
  if (color === "var(--color-accent)") return colors.accent;
  if (color === "var(--color-ai)") return colors.violet;
  if (color === "var(--color-network)") return colors.teal;
  if (color === "var(--color-storage)") return colors.yellow;
  if (color === "var(--color-activity)") return colors.orange;
  if (color === "var(--color-danger)") return colors.coral;
  if (!color.startsWith("var(")) return color;
  return fallback;
}

export default function BarChart({
  title,
  unit,
  items,
  color,
  emptyDescription = "No grouped totals were recorded for this period.",
  includeZeros = false,
}: BarChartProps) {
  const colors = useChartColors();
  const bars = includeZeros
    ? items.map((item) => ({ name: item.name, count: item.count }))
    : namedCountBars(items);
  const height = Math.max(240, bars.length * 36);
  const fill = resolveColor(color, colors.violet, colors);

  return (
    <div>
      <ChartHeading title={title} unit={unit} />
      {bars.length === 0 ? (
        <ChartEmpty title={EMPTY_TELEMETRY_MESSAGE} description={emptyDescription} />
      ) : (
        <div className="w-full" style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <ReBarChart data={bars} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: colors.subtle, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fill: colors.muted, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value: string) =>
                  value.length > 16 ? `${value.slice(0, 14)}…` : value
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 6,
                  color: colors.ink,
                  fontSize: 12,
                }}
                formatter={(value) => [`${Number(value)} ${unit}`, title]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} isAnimationActive={false} barSize={18}>
                {bars.map((item, index) => (
                  <Cell
                    key={item.name}
                    fill={color ? fill : colors.series[index % colors.series.length]}
                  />
                ))}
              </Bar>
            </ReBarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
