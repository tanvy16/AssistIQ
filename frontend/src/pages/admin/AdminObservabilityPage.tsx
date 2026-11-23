import { useMemo, useState } from "react";

import BarChart from "../../components/charts/BarChart";
import DonutChart from "../../components/charts/DonutChart";
import EvaluationChart from "../../components/charts/EvaluationChart";
import TimeSeriesChart from "../../components/charts/TimeSeriesChart";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import RefreshMeta from "../../components/ui/RefreshMeta";
import StatCard from "../../components/ui/StatCard";
import { useAuth } from "../../context/AuthContext";
import { useChartColors } from "../../lib/chartTheme";
import { useObservability } from "../../lib/useObservability";
import type {
  ObservabilityDashboard,
  TimeRangeKey,
} from "../../lib/observability.types";
import {
  EMPTY_TELEMETRY_MESSAGE,
  ESTIMATED_COST_LABEL,
  MOCK_IAM_LABEL,
  MOCK_IT_EXECUTION_LABEL,
  NOT_EVALUATED_LABEL,
  TIME_RANGE_OPTIONS,
  comparisonRows,
  evaluationDisplay,
  formatCount,
  formatEstimatedCost,
  formatMs,
  formatPercent,
  formatTokens,
  modelTypeLabel,
} from "../../lib/observabilityMetrics";

export default function AdminObservabilityPage() {
  const { accessToken } = useAuth();
  const [range, setRange] = useState<TimeRangeKey>("7d");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const customIncomplete = range === "custom" && (!customStart || !customEnd);
  const { data, error, isLoading, updatedAt, live } = useObservability(
    accessToken,
    range,
    customStart,
    customEnd,
  );

  if (!accessToken) return null;

  return (
    <div className="space-y-5">
      <PageHeader
        title="AI Observability"
        description="Operational telemetry for the selected window. Charts use recorded inference data only."
        actions={
          <div className="flex flex-col items-stretch gap-2 sm:items-end">
            <div className="flex flex-wrap justify-end gap-2">
              {TIME_RANGE_OPTIONS.map((option) => (
                <Button
                  key={option.key}
                  size="sm"
                  variant={range === option.key ? "primary" : "secondary"}
                  onClick={() => setRange(option.key)}
                >
                  {option.label}
                </Button>
              ))}
              <Button
                size="sm"
                variant={range === "custom" ? "primary" : "secondary"}
                onClick={() => setRange("custom")}
              >
                Custom
              </Button>
            </div>
            <RefreshMeta live={live} updatedAt={updatedAt} staleReason={error} />
            {isLoading && data ? (
              <p className="text-[11px] text-ink-subtle">Refreshing this range…</p>
            ) : null}
          </div>
        }
      />

      {range === "custom" ? (
        <Panel title="Custom date range">
          <div className="flex flex-wrap gap-3">
            <label className="text-sm text-ink-muted">
              Start
              <input
                type="datetime-local"
                className="field-control mt-1"
                value={customStart}
                onChange={(event) => setCustomStart(event.target.value)}
              />
            </label>
            <label className="text-sm text-ink-muted">
              End
              <input
                type="datetime-local"
                className="field-control mt-1"
                value={customEnd}
                onChange={(event) => setCustomEnd(event.target.value)}
              />
            </label>
          </div>
          {customIncomplete ? (
            <p className="mt-3 text-sm text-ink-muted">
              Select a start and end time to load telemetry for a custom window.
            </p>
          ) : null}
        </Panel>
      ) : null}

      {isLoading && !data ? <LoadingState label="Loading observability…" /> : null}
      {!isLoading && error && !data ? (
        <EmptyState title="Unable to load observability" description={error} />
      ) : null}

      {data ? (
        <>
          <OverviewSection data={data} />
          <ModelUsageSection data={data} />
          <ModelEvaluationSection data={data} />
          <RagSection data={data} />
          <ChatSection data={data} />
          <ITWorkflowSection data={data} />
          <PasswordResetSection data={data} />
          <AnomalySection data={data} />
          <ModelComparisonSection data={data} />
        </>
      ) : null}
    </div>
  );
}

function OverviewSection({ data }: { data: ObservabilityDashboard }) {
  const colors = useChartColors();
  const window = data.summary.window;
  const failed = data.usage.counts.failed;
  const total = data.usage.counts.total;
  const successTone =
    total === 0 ? "default" : failed > 0 && (data.summary.success_rate ?? 1) < 0.95 ? "danger" : "success";

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        <StatCard label="Total AI requests" value={formatCount(data.summary.total_ai_requests)} />
        <StatCard
          label="Success rate"
          value={formatPercent(data.summary.success_rate)}
          hint={total === 0 ? "No requests in this window" : `${failed} failed`}
          tone={successTone}
        />
        <StatCard
          label="Average latency"
          value={formatMs(data.summary.average_latency_ms)}
          tone="activity"
        />
        <StatCard label="P95 latency" value={formatMs(data.summary.p95_latency_ms)} tone="activity" />
        <StatCard
          label="Total LLM tokens"
          value={formatTokens(data.summary.total_llm_tokens)}
          tone="warning"
        />
        <StatCard label={ESTIMATED_COST_LABEL} value={formatEstimatedCost(data.summary.estimated_cost_usd)} />
        <StatCard
          label="Escalation rate"
          value={formatPercent(data.summary.escalation_rate)}
          tone={(data.summary.escalation_rate ?? 0) > 0 ? "danger" : "default"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel className="xl:col-span-2">
          <TimeSeriesChart
            title="Request volume"
            unit="requests / day"
            points={data.usage.over_time}
            color={colors.accent}
            fillMissingDays
            windowStart={window.start}
            windowEnd={window.end}
          />
        </Panel>
        <Panel>
          <DonutChart
            title="Request outcomes"
            unit="requests"
            centerLabel="requests"
            emptyDescription="No AI requests were recorded in this period, so a success rate is not shown."
            items={[
              { label: "Successful", value: data.usage.counts.successful, color: colors.accent },
              { label: "Failed", value: data.usage.counts.failed, color: colors.coral },
            ]}
          />
        </Panel>
      </div>
    </div>
  );
}

function ModelUsageSection({ data }: { data: ObservabilityDashboard }) {
  const colors = useChartColors();
  const avg = data.latency.overall.average_ms;
  const p95 = data.latency.overall.p95_ms;
  const modelBars = data.models.map((row) => ({
    name: row.model_key ?? row.model_name,
    count: row.requests,
  }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <TimeSeriesChart
            title="Latency over time"
            unit="milliseconds"
            points={data.latency.over_time}
            color={colors.teal}
            emptyDescription="Not enough daily latency samples to plot a series. Average and P95 below are window aggregates, not invented history."
            references={[
              ...(avg != null ? [{ label: `Avg ${Math.round(avg)} ms`, value: avg, color: colors.teal }] : []),
              ...(p95 != null ? [{ label: `P95 ${Math.round(p95)} ms`, value: p95, color: colors.orange }] : []),
            ]}
          />
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <StatCard label="P50" value={formatMs(data.latency.overall.p50_ms)} tone="activity" />
            <StatCard label="P95" value={formatMs(data.latency.overall.p95_ms)} tone="activity" />
            <StatCard label="P99" value={formatMs(data.latency.overall.p99_ms)} tone="activity" />
          </div>
        </Panel>
        <Panel>
          <BarChart
            title="Model usage"
            unit="requests"
            includeZeros
            emptyDescription="No registered models reported inference requests in this period."
            items={modelBars}
          />
        </Panel>
      </div>

      {data.models.length === 0 ? (
        <Panel title="Model request activity">
          <EmptyState
            title={EMPTY_TELEMETRY_MESSAGE}
            description="No inference telemetry was recorded in this period."
          />
        </Panel>
      ) : (
        <Panel title="Model request activity" description="Aggregated inference telemetry for this window.">
          <ModelActivityTable data={data} />
          <div className="mt-4">
            <DataTable
              columns={[
                "Model",
                "Type",
                "Provider",
                "Requests",
                "Success",
                "Avg latency",
                "P95",
                "Tokens",
                ESTIMATED_COST_LABEL,
              ]}
              rows={data.models.map((row) => [
                row.model_key ?? row.model_name,
                modelTypeLabel(row.model_type),
                row.provider,
                String(row.requests),
                formatPercent(row.success_rate),
                formatMs(row.average_latency_ms),
                formatMs(row.p95_latency_ms),
                formatTokens(row.total_tokens, row.tokens_unknown_requests),
                formatEstimatedCost(row.estimated_cost_usd),
              ])}
            />
          </div>
        </Panel>
      )}
    </div>
  );
}

function ModelEvaluationSection({ data }: { data: ObservabilityDashboard }) {
  return (
    <Panel
      title="Model Evaluation"
      description="Ground-truth metrics only. Operational latency is not a performance score."
    >
      {data.evaluations.length === 0 ? (
        <EmptyState title={NOT_EVALUATED_LABEL} description="No models are registered, so comparison cannot be shown." />
      ) : (
        <div className="space-y-5">
          <EvaluationChart evaluations={data.evaluations} />
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-surface-muted text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
                  <th className="px-3 py-2 font-medium">Model</th>
                  <th className="px-3 py-2 font-medium">Classification</th>
                  <th className="px-3 py-2 font-medium">Regression</th>
                  <th className="px-3 py-2 font-medium">Generation</th>
                </tr>
              </thead>
              <tbody>
                {data.evaluations.map((row) => (
                  <tr key={row.model_id} className="border-b border-surface-divider align-top">
                    <td className="px-3 py-3">
                      <p className="font-medium text-ink">{row.model_key}</p>
                      <p className="mt-1">
                        <Badge variant="muted">{modelTypeLabel(row.model_type)}</Badge>
                      </p>
                    </td>
                    <td className="px-3 py-3">
                      <EvalBlock
                        set={row.classification}
                        metrics={["accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc"]}
                      />
                    </td>
                    <td className="px-3 py-3">
                      <EvalBlock set={row.regression} metrics={["mae", "mse", "rmse", "r2"]} />
                    </td>
                    <td className="px-3 py-3">
                      <EvalBlock
                        set={row.llm_generation}
                        metrics={["groundedness", "faithfulness", "relevance", "citation_correctness"]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Panel>
  );
}

function RagSection({ data }: { data: ObservabilityDashboard }) {
  const retrieval = data.rag.retrieval;
  const generation = data.rag.generation;
  const interactions = Number(retrieval.interactions ?? 0);
  return (
    <Panel title="RAG Observability" description={data.rag.notes}>
      {interactions === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="Chat retrieval telemetry has not been recorded for this period." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <h3 className="mb-3 text-sm font-semibold text-ink">Retrieval Metrics</h3>
            <MetricList
              items={[
                ["Average retrieval latency", formatMs((retrieval.latency as { average_ms?: number | null })?.average_ms)],
                ["P50 retrieval latency", formatMs((retrieval.latency as { p50_ms?: number | null })?.p50_ms)],
                ["P95 retrieval latency", formatMs((retrieval.latency as { p95_ms?: number | null })?.p95_ms)],
                ["Average Top-K", formatCount(retrieval.average_top_k as number | null)],
                ["Retrieved chunks", formatCount(retrieval.average_retrieved_chunks as number | null)],
                ["Average similarity", retrieval.average_similarity == null ? "—" : Number(retrieval.average_similarity).toFixed(3)],
                ["Precision@K", String(retrieval.precision_at_k ?? NOT_EVALUATED_LABEL)],
                ["Recall@K", String(retrieval.recall_at_k ?? NOT_EVALUATED_LABEL)],
                ["Hit Rate@K", String(retrieval.hit_rate_at_k ?? NOT_EVALUATED_LABEL)],
                ["MRR", String(retrieval.mrr ?? NOT_EVALUATED_LABEL)],
              ]}
            />
          </div>
          <div>
            <h3 className="mb-3 text-sm font-semibold text-ink">Generation Metrics</h3>
            <MetricList
              items={[
                ["Groundedness", String(generation.groundedness ?? NOT_EVALUATED_LABEL)],
                ["Faithfulness", String(generation.faithfulness ?? NOT_EVALUATED_LABEL)],
                ["Relevance", String(generation.relevance ?? NOT_EVALUATED_LABEL)],
                ["Citation correctness", String(generation.citation_correctness ?? NOT_EVALUATED_LABEL)],
                ["Citation completeness", String(generation.citation_completeness ?? NOT_EVALUATED_LABEL)],
                ["Citation coverage", formatPercent(generation.citation_rate as number | null)],
              ]}
            />
          </div>
        </div>
      )}
    </Panel>
  );
}

function ChatSection({ data }: { data: ObservabilityDashboard }) {
  const chat = data.chat;
  return (
    <Panel title="Chatbot" description="Conversation telemetry from recorded chat interactions.">
      {chat.messages === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="No chat interactions were recorded in this period." />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Conversations" value={formatCount(chat.conversations)} />
            <StatCard label="AI responses" value={formatCount(chat.messages)} tone="ai" />
            <StatCard label="Average response time" value={formatMs(chat.latency.average_ms)} tone="activity" />
            <StatCard label="P95 response time" value={formatMs(chat.latency.p95_ms)} tone="activity" />
            <StatCard label="Escalation %" value={formatPercent(chat.escalation_rate)} />
            <StatCard label="Citation coverage" value={formatPercent(chat.citation_rate)} />
            <StatCard label="Average retrieval score" value={chat.average_similarity == null ? "—" : chat.average_similarity.toFixed(3)} />
            <StatCard label="Retrieval latency" value={formatMs(chat.retrieval_latency.average_ms)} tone="network" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <BarChart title="Intent distribution" unit="messages" color="var(--color-ai)" items={chat.intents} />
            <BarChart title="Confidence states" unit="messages" color="var(--color-network)" items={chat.confidence} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function ITWorkflowSection({ data }: { data: ObservabilityDashboard }) {
  const workflow = data.itWorkflows;
  return (
    <Panel title="IT Workflow" description={MOCK_IT_EXECUTION_LABEL}>
      {workflow.total_requests === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="No IT workflow requests were recorded in this period." />
      ) : (
        <div className="space-y-4">
          <p className="rounded border border-activity bg-activity-soft px-3 py-2 text-sm text-ink">
            {workflow.execution_mode}
          </p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Requests" value={formatCount(workflow.total_requests)} />
            <StatCard label="Policy allow" value={formatPercent(workflow.policy_allow_rate)} tone="success" />
            <StatCard label="Approval required" value={formatPercent(workflow.approval_required_rate)} tone="warning" />
            <StatCard label="Denial" value={formatPercent(workflow.denial_rate)} tone="danger" />
            <StatCard label="Escalation" value={formatPercent(workflow.escalation_rate)} />
            <StatCard label="Simulated execution success" value={formatPercent(workflow.execution_success_rate)} />
            <StatCard label="Validation" value={formatPercent(workflow.validation_success_rate)} />
            <StatCard label="Rollback" value={formatPercent(workflow.rollback_rate)} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <BarChart title="Requests by type" unit="requests" color="var(--color-network)" items={workflow.by_type} />
            <BarChart title="Policy outcomes" unit="requests" color="var(--color-storage)" items={workflow.by_policy} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function PasswordResetSection({ data }: { data: ObservabilityDashboard }) {
  const resets = data.passwordResets;
  return (
    <Panel title="Password Reset" description={MOCK_IAM_LABEL}>
      {resets.total_requests === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="No password reset requests were recorded in this period." />
      ) : (
        <div className="space-y-4">
          <p className="rounded border border-activity bg-activity-soft px-3 py-2 text-sm text-ink">
            {resets.execution_mode}
          </p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Requests" value={formatCount(resets.total_requests)} />
            <StatCard label="Verification success" value={formatPercent(resets.verification_success_rate)} tone="success" />
            <StatCard label="Verification failure" value={formatPercent(resets.verification_failure_rate)} tone="danger" />
            <StatCard label="Confirmation" value={formatPercent(resets.confirmation_rate)} />
            <StatCard label="Completion" value={formatPercent(resets.completion_rate)} />
            <StatCard label="Failure" value={formatPercent(resets.failure_rate)} tone="danger" />
            <StatCard label="Escalation" value={formatPercent(resets.escalation_rate)} />
            <StatCard label="Average workflow latency" value={formatMs(resets.stage_latency.total_ms)} tone="activity" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <BarChart title="Risk distribution" unit="requests" color="var(--color-storage)" items={resets.by_risk} />
            <BarChart title="Policy decisions" unit="requests" color="var(--color-ai)" items={resets.by_policy} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function AnomalySection({ data }: { data: ObservabilityDashboard }) {
  return (
    <Panel title="Anomalies" description="Explainable threshold checks against the previous 7-day baseline.">
      {data.anomalies.length === 0 ? (
        <EmptyState title="No anomalies detected" description="Latency, failures, tokens, volume, escalations, and retrieval latency are within configured thresholds." />
      ) : (
        <DataTable
          columns={["Severity", "Metric", "Observed", "Baseline", "Explanation", "Timestamp"]}
          rows={data.anomalies.map((item) => [
            item.severity,
            item.metric,
            String(item.observed_value),
            item.baseline_value == null ? "—" : String(item.baseline_value),
            item.explanation,
            new Date(item.timestamp).toLocaleString(),
          ])}
        />
      )}
    </Panel>
  );
}

function ModelComparisonSection({ data }: { data: ObservabilityDashboard }) {
  const rows = comparisonRows(data.evaluations, data.models);
  return (
    <Panel title="Model Comparison" description="Evaluation scores require ground truth. Latency and requests come from operational telemetry.">
      {rows.length === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="Register models to compare accuracy, F1, latency, and request volume." />
      ) : (
        <DataTable
          columns={["Model", "Type", "Accuracy", "F1", "Latency", "Requests"]}
          rows={rows.map((row) => [row.model, row.type, row.accuracy, row.f1, row.latency, String(row.requests)])}
        />
      )}
    </Panel>
  );
}

function MetricList({ items }: { items: [string, string][] }) {
  return (
    <dl className="space-y-2 text-sm">
      {items.map(([label, value]) => (
        <div key={label} className="flex items-start justify-between gap-4">
          <dt className="text-ink-muted">{label}</dt>
          <dd className="font-medium text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function EvalBlock({
  set,
  metrics,
}: {
  set: ObservabilityDashboard["evaluations"][number]["classification"];
  metrics: string[];
}) {
  if (set.status === "Not evaluated") {
    return <p className="text-sm text-ink-muted">{NOT_EVALUATED_LABEL}</p>;
  }
  return <MetricList items={metrics.map((metric) => [metric, evaluationDisplay(set, metric)])} />;
}

function ModelActivityTable({ data }: { data: ObservabilityDashboard }) {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return data.models.filter((row) => {
      if (!needle) return true;
      const haystack = `${row.model_key ?? ""} ${row.model_name} ${row.provider} ${row.model_type}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [data.models, query]);

  return (
    <div className="space-y-3">
      <label className="block max-w-xs text-sm text-ink-muted">
        Filter models
        <input
          className="field-control mt-1"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Model, provider, or type"
        />
      </label>
      {rows.length === 0 ? (
        <EmptyState title={EMPTY_TELEMETRY_MESSAGE} description="No model rows match this filter." />
      ) : (
        <DataTable
          columns={["Model", "Type", "Requests", "Failed", "Success rate"]}
          rows={rows.map((row) => [
            row.model_key ?? row.model_name,
            modelTypeLabel(row.model_type),
            String(row.requests),
            String(row.failed),
            formatPercent(row.success_rate),
          ])}
        />
      )}
    </div>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-surface-border bg-surface-muted text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
            {columns.map((column) => (
              <th key={column} className="px-3 py-2 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row[0]}-${index}`} className="border-b border-surface-divider hover:bg-surface-hover">
              {row.map((cell, cellIndex) => (
                <td key={`${columns[cellIndex]}-${cellIndex}`} className="px-3 py-3 text-ink">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
