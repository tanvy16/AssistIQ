import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { evaluationChartRows, firstEvaluatedKind } from "../../lib/chartSeries";
import { CHART_HEIGHT, useChartColors } from "../../lib/chartTheme";
import { NOT_EVALUATED_LABEL } from "../../lib/observabilityMetrics";
import type { ModelEvaluationRow } from "../../lib/observability.types";
import { ChartEmpty, ChartHeading } from "./ChartFrame";

const KIND_LABEL: Record<"classification" | "regression" | "llm_generation", string> = {
  classification: "Classification metrics",
  regression: "Regression metrics",
  llm_generation: "Generation metrics",
};

export default function EvaluationChart({ evaluations }: { evaluations: ModelEvaluationRow[] }) {
  const colors = useChartColors();
  const kind = firstEvaluatedKind(evaluations);
  const { rows, keys } = kind ? evaluationChartRows(evaluations, kind) : { rows: [], keys: [] };
  const bounded = kind === "classification" || kind === "llm_generation";

  return (
    <div>
      <ChartHeading
        title="Model performance"
        unit={kind ? KIND_LABEL[kind] : "Ground-truth evaluation only"}
      />
      {!kind || rows.length === 0 ? (
        <ChartEmpty
          title={NOT_EVALUATED_LABEL}
          description="Registered models have no stored ground-truth evaluation results. Operational latency and request counts are not performance scores."
        />
      ) : (
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: colors.muted, fontSize: 11 }}
                axisLine={{ stroke: colors.grid }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: colors.subtle, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
                domain={bounded ? [0, 1] : ["auto", "auto"]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 6,
                  color: colors.ink,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: colors.muted }} />
              {keys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={colors.series[index % colors.series.length]}
                  radius={[3, 3, 0, 0]}
                  isAnimationActive={false}
                  maxBarSize={36}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
