import { Link } from "react-router-dom";

import StatusMix from "../../components/charts/StatusMix";
import DataUnavailable from "../../components/ui/DataUnavailable";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import { PanelSkeleton } from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import RefreshMeta from "../../components/ui/RefreshMeta";
import StatCard from "../../components/ui/StatCard";
import TicketTable from "../../components/tickets/TicketTable";
import { useAuth } from "../../context/AuthContext";
import { formatDateTime, formatEventLabel } from "../../lib/ticketLabels";
import { useDashboard } from "../../lib/useDashboard";

export default function EmployeeDashboard() {
  const { user, accessToken } = useAuth();
  const displayName = user?.display_name ?? user?.email ?? "there";
  const { data, error, isLoading, updatedAt, live, refresh } = useDashboard(accessToken);
  const tickets = data?.tickets;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome, ${displayName}`}
        description="Track your requests and get AI-assisted IT support."
        actions={
          <>
            <Link to="/app/employee/tickets/new">
              <Button variant="primary">Create Ticket</Button>
            </Link>
            <Link to="/app/employee/chat">
              <Button variant="secondary">Ask AssistIQ</Button>
            </Link>
            <Link to="/app/employee/tickets">
              <Button variant="secondary">View My Tickets</Button>
            </Link>
          </>
        }
      />

      <RefreshMeta live={live} updatedAt={updatedAt} staleReason={error} />
      {error && !data && !isLoading ? (
        <DataUnavailable error={error} onRetry={refresh} subject="your dashboard" />
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
          <StatCard label="My tickets" value={tickets?.total ?? 0} />
          <StatCard label="Open" value={tickets?.open ?? 0} tone="network" />
          <StatCard label="In progress" value={tickets?.in_progress ?? 0} tone="ai" />
          <StatCard label="Resolved" value={tickets?.resolved ?? 0} tone="success" />
        </div>
      )}

      <Panel>
        <StatusMix tickets={tickets} />
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="My tickets" description="Tickets you have submitted">
          <TicketTable
            tickets={data?.recent_tickets ?? []}
            detailBasePath="/app/employee/tickets"
            emptyMessage="You have not submitted any tickets yet."
          />
        </Panel>
        <Panel title="Recent activity" description="Latest updates on your requests">
          {!data?.recent_activity.length ? (
            <EmptyState
              title="No recent activity"
              description="Updates from your tickets will appear here."
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
      </>
      )}
    </div>
  );
}
