import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { hasAnyDailyActivity, shortDayLabel, type DailyTicketPoint } from "../../lib/analytics";
import { CHART_HEIGHT, useChartColors } from "../../lib/chartTheme";
import { ChartEmpty, ChartHeading } from "./ChartFrame";

type SeriesKey = "created" | "resolved" | "escalations" | "chat_tickets";

type DailyMultiSeriesChartProps = {
  title: string;
  unit: string;
  points: DailyTicketPoint[];
  series: { key: SeriesKey; label: string; color: "accent" | "teal" | "violet" | "orange" | "coral" | "yellow" }[];
  emptyDescription: string;
};

/** Grouped daily bars. Zero-filled days come from the API; an all-zero window shows an empty state. */
export default function DailyMultiSeriesChart({
  title,
  unit,
  points,
  series,
  emptyDescription,
}: DailyMultiSeriesChartProps) {
  const colors = useChartColors();
  const keys = series.map((item) => item.key);

  if (!hasAnyDailyActivity(points, keys)) {
    return (
      <div>
        <ChartHeading title={title} unit={unit} />
        <ChartEmpty title="No activity recorded in this window" description={emptyDescription} />
      </div>
    );
  }

  const data = points.map((point) => ({ ...point, label: shortDayLabel(point.date) }));

  return (
    <div>
      <ChartHeading title={title} unit={unit} />
      <div style={{ height: CHART_HEIGHT }} role="img" aria-label={`${title}: grouped daily bar chart`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 0 }} barCategoryGap="20%">
            <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: colors.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: colors.border }}
              interval="preserveStartEnd"
              minTickGap={12}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: colors.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              cursor={{ fill: colors.grid, opacity: 0.35 }}
              contentStyle={{
                background: colors.tooltipBg,
                border: `1px solid ${colors.border}`,
                borderRadius: 6,
                color: colors.ink,
                fontSize: 12,
              }}
              labelStyle={{ color: colors.ink, fontWeight: 600 }}
              formatter={(value, name) => [typeof value === "number" ? value.toLocaleString() : String(value ?? ""), String(name ?? "")]}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, color: colors.muted, paddingTop: 4 }}
              iconType="square"
              iconSize={10}
            />
            {series.map((item) => (
              <Bar
                key={item.key}
                dataKey={item.key}
                name={item.label}
                fill={colors[item.color]}
                radius={[2, 2, 0, 0]}
                maxBarSize={18}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
