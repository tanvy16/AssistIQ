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
import TicketTable from "../../components/tickets/TicketTable";
import { useAuth } from "../../context/AuthContext";
import { formatSlaCompliance } from "../../lib/dashboard";
import { formatDateTime, formatEventLabel } from "../../lib/ticketLabels";
import { useDashboard } from "../../lib/useDashboard";

export default function AdminDashboard() {
  const { user, accessToken } = useAuth();
  const displayName = user?.display_name ?? user?.email ?? "Admin";
  const { data, error, isLoading, updatedAt, live, refresh } = useDashboard(accessToken);
  const tickets = data?.tickets;
  const users = data?.users;
  const knowledge = data?.knowledge;
  const ai = data?.ai;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Administration — ${displayName}`}
        description="Operational overview of tickets, knowledge, AI usage, and platform health."
        actions={
          <>
            <Link to="/app/admin/tickets">
              <Button variant="primary">Tickets</Button>
            </Link>
            <Link to="/app/admin/knowledge">
              <Button variant="secondary">Knowledge Base</Button>
            </Link>
            <Link to="/app/admin/observability">
              <Button variant="secondary">Observability</Button>
            </Link>
            <Link to="/app/admin/audits">
              <Button variant="secondary">Audit Log</Button>
            </Link>
            <Link to="/app/admin/users">
              <Button variant="secondary">Users</Button>
            </Link>
          </>
        }
      />

      <RefreshMeta live={live} updatedAt={updatedAt} staleReason={error} />
      {error && !data && !isLoading ? (
        <DataUnavailable error={error} onRetry={refresh} subject="dashboard metrics" />
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
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total tickets" value={tickets?.total ?? 0} />
            <StatCard label="Open" value={tickets?.open ?? 0} tone="network" />
            <StatCard label="In progress" value={tickets?.in_progress ?? 0} tone="ai" />
            <StatCard label="Resolved" value={tickets?.resolved ?? 0} tone="success" />
            <StatCard
              label="SLA compliance"
              value={formatSlaCompliance(tickets?.sla_compliance_pct ?? null)}
              hint={`${tickets?.sla_at_risk ?? 0} at risk · ${tickets?.sla_breached ?? 0} overdue`}
              tone={(tickets?.sla_breached ?? 0) > 0 ? "danger" : "default"}
            />
            <StatCard
              label="Active agents"
              value={users?.active_agents ?? 0}
              hint={`${users?.total ?? 0} users total`}
            />
            <StatCard
              label="AI requests (7d)"
              value={ai?.request_count ?? 0}
              tone="ai"
              hint={
                ai?.total_tokens != null
                  ? `${ai.total_tokens.toLocaleString()} tokens recorded`
                  : `${ai?.successful ?? 0} successful · ${ai?.failed ?? 0} failed`
              }
            />
            <StatCard
              label="Service health"
              value={data?.health.database === "connected" ? "Healthy" : "Degraded"}
              hint={`API ${data?.health.api ?? "—"} · DB ${data?.health.database ?? "—"}`}
              tone={data?.health.database === "connected" ? "success" : "danger"}
            />
          </div>

          <Panel>
            <StatusMix tickets={tickets} />
          </Panel>

          <div className="grid gap-4 lg:grid-cols-3">
            <Panel title="Knowledge base" description="Published and draft articles">
              {knowledge ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-ink-muted">Total</dt>
                    <dd className="text-lg font-semibold text-ink">{knowledge.total}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Published</dt>
                    <dd className="text-lg font-semibold text-ink">{knowledge.published}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Draft</dt>
                    <dd className="text-lg font-semibold text-ink">{knowledge.draft}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Archived</dt>
                    <dd className="text-lg font-semibold text-ink">{knowledge.archived}</dd>
                  </div>
                </dl>
              ) : (
                <EmptyState title="No knowledge data" description="Knowledge statistics will appear once documents are available." />
              )}
            </Panel>

            <Panel title="Users" description="Directory counts by role">
              {users ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-ink-muted">Employees</dt>
                    <dd className="text-lg font-semibold text-ink">{users.employees}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Agents</dt>
                    <dd className="text-lg font-semibold text-ink">{users.agents}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Admins</dt>
                    <dd className="text-lg font-semibold text-ink">{users.admins}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Active</dt>
                    <dd className="text-lg font-semibold text-ink">{users.active}</dd>
                  </div>
                </dl>
              ) : (
                <LoadingState label="Loading users…" />
              )}
            </Panel>

            <Panel title="AI usage" description="Inference telemetry from the last 7 days">
              {ai ? (
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-ink-muted">Requests</dt>
                    <dd className="font-medium text-ink">{ai.request_count}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-ink-muted">Successful</dt>
                    <dd className="font-medium text-ink">{ai.successful}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-ink-muted">Failed</dt>
                    <dd className="font-medium text-ink">{ai.failed}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-ink-muted">Tokens</dt>
                    <dd className="font-medium text-ink">
                      {ai.total_tokens == null ? "Not recorded" : ai.total_tokens.toLocaleString()}
                    </dd>
                  </div>
                </dl>
              ) : (
                <EmptyState
                  title="No AI telemetry yet"
                  description="Request counts appear after chat or model inference runs."
                />
              )}
            </Panel>
          </div>
        </>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Recent activity" description="Latest ticket events across the organization">
          {!data?.recent_activity.length ? (
            <EmptyState
              title="No recent activity"
              description="Ticket creation, assignment, and status changes will appear here."
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
        <Panel title="Recent tickets" description="Newest tickets visible to administration">
          <TicketTable
            tickets={data?.recent_tickets ?? []}
            detailBasePath="/app/admin/tickets"
            emptyMessage="No tickets have been created yet."
          />
        </Panel>
      </div>
      </>
      )}
    </div>
  );
}
