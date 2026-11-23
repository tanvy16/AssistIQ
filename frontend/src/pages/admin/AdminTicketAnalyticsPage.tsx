import { useCallback, useEffect, useRef, useState } from "react";

import BarChart from "../../components/charts/BarChart";
import DailyMultiSeriesChart from "../../components/charts/DailyMultiSeriesChart";
import DonutChart from "../../components/charts/DonutChart";
import Button from "../../components/ui/Button";
import DataUnavailable from "../../components/ui/DataUnavailable";
import { PanelSkeleton } from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import StatCard from "../../components/ui/StatCard";
import { useAuth } from "../../context/AuthContext";
import {
  ANALYTICS_WINDOWS,
  fetchTicketAnalytics,
  type AnalyticsWindow,
  type TicketAnalytics,
} from "../../lib/analytics";
import { categoryLabels, priorityLabels, statusLabels } from "../../lib/ticketLabels";

// Same semantic colours as the status badges and the dashboard status bar.
const STATUS_COLORS: Record<keyof TicketAnalytics["status"], string> = {
  open: "var(--color-network)",
  in_progress: "var(--color-ai)",
  pending: "var(--color-activity)",
  resolved: "var(--color-accent)",
  closed: "var(--color-ink-subtle)",
};

function formatSnapshotTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(iso));
}

export default function AdminTicketAnalyticsPage() {
  const { accessToken } = useAuth();
  const [days, setDays] = useState<AnalyticsWindow>(30);
  const [data, setData] = useState<TicketAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const controllerRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) return;
    // Cancel an obsolete request (e.g. the user switched range mid-flight).
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    try {
      const next = await fetchTicketAnalytics(accessToken, days, controller.signal);
      if (controller.signal.aborted) return;
      setData(next);
      setError(null);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [accessToken, days]);

  useEffect(() => {
    void load();
    return () => controllerRef.current?.abort();
  }, [load]);

  const stale = data && data.window_days !== days;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ticket analytics"
        description="Ticket volume, resolution, SLA and escalation trends computed from persisted ticket and escalation records."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded border border-surface-border bg-surface p-0.5" role="group" aria-label="Date range">
          {ANALYTICS_WINDOWS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={days === option}
              onClick={() => setDays(option)}
              className={`rounded-sm px-3 py-1 text-xs font-medium transition ${
                days === option ? "bg-accent-soft text-accent" : "text-ink-muted hover:text-ink"
              }`}
            >
              {option} days
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="inline-flex items-center gap-1.5 rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 font-medium uppercase tracking-wide text-ink-subtle">
            Snapshot
          </span>
          <span className="text-ink-subtle">
            {loading ? "Loading…" : data ? `Taken ${formatSnapshotTime(data.generated_at)} · not auto-refreshing` : ""}
          </span>
          <Button variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      {error && data ? <p className="text-xs text-danger">Refresh failed: {error}. Showing the previous snapshot.</p> : null}
      {error && !data && !loading ? <DataUnavailable error={error} onRetry={() => void load()} subject="ticket analytics" /> : null}

      {!data && loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <PanelSkeleton />
          <PanelSkeleton />
        </div>
      ) : null}

      {data ? (
        <div className={`space-y-6 transition-opacity ${stale || loading ? "opacity-60" : ""}`} aria-busy={loading}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label={`Created (${data.window_days}d)`} value={data.totals.created} tone="network" />
            <StatCard label={`Resolved (${data.window_days}d)`} value={data.totals.resolved} tone="success" />
            <StatCard
              label="SLA met on resolution"
              value={data.sla.compliance_pct == null ? "—" : `${data.sla.compliance_pct}%`}
              hint={
                data.sla.compliance_pct == null
                  ? "No tickets resolved in this window"
                  : `${data.sla.resolved_within_sla} within · ${data.sla.resolved_after_sla} late`
              }
            />
            <StatCard
              label={`Chat escalations (${data.window_days}d)`}
              value={data.totals.escalations}
              tone="ai"
              hint={`${data.totals.chat_tickets} ticket${data.totals.chat_tickets === 1 ? "" : "s"} created from chat`}
            />
          </div>

          <Panel>
            <DailyMultiSeriesChart
              title="Tickets created vs resolved"
              unit="tickets per day (UTC)"
              points={data.daily}
              series={[
                { key: "created", label: "Created", color: "teal" },
                { key: "resolved", label: "Resolved", color: "accent" },
              ]}
              emptyDescription="No tickets were created or resolved in the selected window. Nothing is drawn rather than inventing a trend."
            />
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel>
              <DonutChart
                title="Current status distribution"
                unit="all tickets, now"
                centerLabel="tickets"
                items={(Object.keys(data.status) as (keyof TicketAnalytics["status"])[]).map((status) => ({
                  label: statusLabels[status],
                  value: data.status[status],
                  color: STATUS_COLORS[status],
                }))}
                emptyDescription="No tickets exist yet."
              />
            </Panel>
            <Panel>
              <BarChart
                title="Active tickets by priority"
                unit="open, in progress and pending"
                includeZeros
                items={(Object.keys(data.active_by_priority) as (keyof TicketAnalytics["active_by_priority"])[]).map(
                  (priority) => ({ name: priorityLabels[priority], count: data.active_by_priority[priority] }),
                )}
                emptyDescription="There are no active tickets."
              />
            </Panel>
            <Panel>
              <DonutChart
                title="SLA status of active tickets"
                unit="due-date position right now"
                centerLabel="active"
                items={[
                  { label: "On track", value: data.sla.active_on_track, color: "var(--color-accent)" },
                  { label: "At risk (< 1 h)", value: data.sla.active_at_risk, color: "var(--color-storage)" },
                  { label: "Breached", value: data.sla.active_breached, color: "var(--color-danger)" },
                ]}
                emptyDescription="There are no active tickets with an SLA due date."
              />
            </Panel>
            <Panel>
              <BarChart
                title={`Tickets created by category (${data.window_days}d)`}
                unit="tickets"
                includeZeros
                items={Object.entries(data.created_by_category).map(([category, count]) => ({
                  name: categoryLabels[category as keyof typeof categoryLabels] ?? category,
                  count,
                }))}
                emptyDescription="No tickets were created in this window."
              />
            </Panel>
          </div>

          <Panel>
            <DailyMultiSeriesChart
              title="Human escalations from AI chat"
              unit="per day (UTC)"
              points={data.daily}
              series={[
                { key: "escalations", label: "Escalation requests", color: "violet" },
                { key: "chat_tickets", label: "Tickets created from chat", color: "orange" },
              ]}
              emptyDescription="No chat conversation was escalated to a human in this window."
            />
          </Panel>
        </div>
      ) : null}
    </div>
  );
}
