import { Link } from "react-router-dom";

import StatusMix from "../../components/charts/StatusMix";
import DataUnavailable from "../../components/ui/DataUnavailable";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState, { PanelSkeleton } from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import RefreshMeta from "../../components/ui/RefreshMeta";
import StatCard from "../../components/ui/StatCard";
import { useAuth } from "../../context/AuthContext";
import { formatSlaCompliance } from "../../lib/dashboard";
import { formatDateTime, formatEventLabel } from "../../lib/ticketLabels";
import { useDashboard } from "../../lib/useDashboard";
import TicketTable from "../../components/tickets/TicketTable";

export default function AgentDashboard() {
  const { user, accessToken } = useAuth();
  const displayName = user?.display_name ?? user?.email ?? "Agent";
  const { data, error, isLoading, updatedAt, live, refresh } = useDashboard(accessToken);

  const tickets = data?.tickets;
  const queueCount = tickets?.unassigned_queue ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Agent workspace — ${displayName}`}
        description="Live queue health, assigned work, and SLA risk from current ticket data."
        actions={
          <>
            <Link to="/app/agent/queue">
              <Button variant="primary">Ticket Queue</Button>
            </Link>
            <Link to="/app/agent/tickets">
              <Button variant="secondary">Assigned Tickets</Button>
            </Link>
            <Link to="/app/agent/chat">
              <Button variant="secondary">AI Chat</Button>
            </Link>
          </>
        }
      />

      <RefreshMeta live={live} updatedAt={updatedAt} staleReason={error} />
      {error && !data && !isLoading ? (
        <DataUnavailable error={error} onRetry={refresh} subject="queue metrics" />
      ) : null}
      {!data ? (
        isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-busy="true">
            <PanelSkeleton />
            <PanelSkeleton />
            <PanelSkeleton />
            <PanelSkeleton />
          </div>
        ) : null
      ) : (
      <>

      {isLoading && !data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PanelSkeleton />
          <PanelSkeleton />
          <PanelSkeleton />
          <PanelSkeleton />
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Open tickets" value={tickets?.open ?? 0} tone="network" />
          <StatCard
            label="Queue"
            value={queueCount}
            hint="Unassigned tickets waiting to be claimed"
            tone={queueCount > 0 ? "warning" : "default"}
          />
          <StatCard label="Assigned to me" value={tickets?.assigned_to_me ?? 0} />
          <StatCard
            label="SLA at risk"
            value={tickets?.sla_at_risk ?? 0}
            hint={tickets?.sla_breached ? `${tickets.sla_breached} already overdue` : "Due within one hour"}
            tone={(tickets?.sla_at_risk ?? 0) > 0 ? "danger" : "default"}
          />
          <StatCard label="Resolved" value={tickets?.resolved ?? 0} tone="success" />
          <StatCard
            label="SLA compliance"
            value={formatSlaCompliance(tickets?.sla_compliance_pct ?? null)}
            hint="Resolved on time among completed tickets"
          />
          <StatCard
            label="Queue health"
            value={tickets?.sla_breached ? "At risk" : queueCount ? "Active" : "Clear"}
            hint={`${tickets?.in_progress ?? 0} in progress · ${tickets?.pending ?? 0} pending`}
            tone={tickets?.sla_breached ? "danger" : queueCount ? "warning" : "success"}
          />
          <StatCard
            label="Database"
            value={data?.health.database === "connected" ? "Connected" : data?.health.database ?? "—"}
            tone={data?.health.database === "connected" ? "success" : "danger"}
          />
        </div>
      )}

      <Panel>
        <StatusMix tickets={tickets} />
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Ticket queue"
          description="Same unassigned tickets shown in Ticket Queue"
        >
          {isLoading && !data ? (
            <LoadingState label="Loading queue…" />
          ) : queueCount === 0 ? (
            <EmptyState
              title="Queue is empty"
              description="There are no unassigned tickets waiting. New requests will appear here automatically."
              action={
                <Link to="/app/agent/queue">
                  <Button variant="secondary" size="sm">
                    Open Ticket Queue
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-ink">
                <span className="font-semibold">{queueCount}</span> unassigned ticket
                {queueCount === 1 ? "" : "s"} ready to claim.
              </p>
              <Link to="/app/agent/queue">
                <Button variant="primary" size="sm">
                  Open Ticket Queue
                </Button>
              </Link>
            </div>
          )}
        </Panel>

        <Panel title="Recent activity" description="Ticket assignments, status changes, and comments">
          {!data?.recent_activity.length ? (
            <EmptyState
              title="No recent activity"
              description="Assignment and status changes across your queue and assigned tickets will appear here."
            />
          ) : (
            <ul className="divide-y divide-surface-border">
              {data.recent_activity.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm text-ink">{item.summary}</p>
                    <p className="text-xs capitalize text-ink-muted">{formatEventLabel(item.event_type)}</p>
                  </div>
                  <p className="shrink-0 text-xs text-ink-muted">{formatDateTime(item.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="My assigned tickets" description="Your current workload">
        <TicketTable
          tickets={data?.recent_tickets ?? []}
          detailBasePath="/app/agent/tickets"
          emptyMessage="No tickets are currently assigned to you."
        />
      </Panel>
      </>
      )}
    </div>
  );
}
