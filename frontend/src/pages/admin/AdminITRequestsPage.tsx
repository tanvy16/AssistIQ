import { useEffect, useState } from "react";

import ITRequestListPage from "../../components/it/ITRequestListPage";
import Panel from "../../components/ui/Panel";
import { useAuth } from "../../context/AuthContext";
import {
  fetchAccessCatalog,
  fetchITRequests,
  fetchRunbooks,
  fetchSoftwareCatalog,
} from "../../lib/itRequests";
import type {
  AccessCatalogItem,
  ITRequestListItem,
  RunbookItem,
  SoftwareCatalogItem,
} from "../../lib/itRequests.types";

export default function AdminITRequestsPage() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<ITRequestListItem[]>([]);
  const [software, setSoftware] = useState<SoftwareCatalogItem[]>([]);
  const [access, setAccess] = useState<AccessCatalogItem[]>([]);
  const [runbooks, setRunbooks] = useState<RunbookItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    const controller = new AbortController();
    void (async () => {
      setIsLoading(true);
      try {
        const [requests, softwareCatalog, accessCatalog, runbookList] = await Promise.all([
          fetchITRequests(accessToken),
          fetchSoftwareCatalog(accessToken),
          fetchAccessCatalog(accessToken),
          fetchRunbooks(accessToken),
        ]);
        if (controller.signal.aborted) return;
        setItems(requests.items);
        setSoftware(softwareCatalog);
        setAccess(accessCatalog);
        setRunbooks(runbookList);
        setError(null);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load IT administration");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    })();
    return () => controller.abort();
  }, [accessToken]);

  if (!accessToken) return null;

  return (
    <div className="space-y-6">
      <ITRequestListPage
        title="IT Requests"
        description="Approve, reject, and inspect simulated catalog executions."
        basePath="/app/admin/it-requests"
        accessToken={accessToken}
        items={items}
        isLoading={isLoading}
        error={error}
      />

      <Panel title="Software catalog">
        <ul className="divide-y divide-surface-border text-sm">
          {software.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="text-ink">{item.name}</span>
              <span className="text-ink-muted">
                {item.risk_level} · {item.enabled ? "enabled" : "disabled"} · {item.runbook_id}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title="Access catalog">
        <ul className="divide-y divide-surface-border text-sm">
          {access.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="text-ink">{item.resource_name}</span>
              <span className="text-ink-muted">
                {item.risk_level} · {item.enabled ? "enabled" : "disabled"}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title="Runbook registry">
        <ul className="divide-y divide-surface-border text-sm">
          {runbooks.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="font-mono text-[13px] text-ink">{item.id}</span>
              <span className="text-ink-muted">
                {item.action_type} · {item.enabled ? "enabled" : "disabled"}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
