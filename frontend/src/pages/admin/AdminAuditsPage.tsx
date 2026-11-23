import { useEffect, useState } from "react";

import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useAuth } from "../../context/AuthContext";
import { fetchAuditEvents } from "../../lib/audits";
import type { AuditEvent } from "../../lib/audits";

export default function AdminAuditsPage() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    void (async () => {
      setIsLoading(true);
      try {
        const response = await fetchAuditEvents(accessToken);
        setItems(response.items);
        setTotal(response.total);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load audit events");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [accessToken]);

  if (!accessToken) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Log"
        description="Append-only security and workflow events. Secrets, tokens, and passwords are never shown."
      />
      {isLoading ? <LoadingState label="Loading audit events…" /> : null}
      {!isLoading && error ? (
        <EmptyState title="Unable to load audit events" description={error} />
      ) : null}
      {!isLoading && !error && items.length === 0 ? (
        <EmptyState
          title="No audit events"
          description="Authentication and workflow events will appear here as they occur."
        />
      ) : null}
      {!isLoading && !error && items.length > 0 ? (
        <Panel title="Recent events" description={`${total} recorded`}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-surface-muted text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
                  <th className="px-3 py-2 font-medium">Time</th>
                  <th className="px-3 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Actor</th>
                  <th className="px-3 py-2 font-medium">Metadata</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-surface-divider hover:bg-surface-hover">
                    <td className="px-3 py-3 text-ink-muted">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-3 font-medium text-ink">{item.event_type}</td>
                    <td className="px-3 py-3 text-ink-muted">{item.user_id ?? "—"}</td>
                    <td className="px-3 py-3 text-ink-muted">
                      {item.payload ? JSON.stringify(item.payload) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
