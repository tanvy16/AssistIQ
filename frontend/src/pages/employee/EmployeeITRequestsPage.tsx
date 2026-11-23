import { useEffect, useState } from "react";

import ITRequestListPage from "../../components/it/ITRequestListPage";
import { useAuth } from "../../context/AuthContext";
import { fetchITRequests } from "../../lib/itRequests";
import type { ITRequestListItem } from "../../lib/itRequests.types";

export default function EmployeeITRequestsPage() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<ITRequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload(force = false) {
    if (!accessToken) return;
    setIsLoading(true);
    try {
      const response = await fetchITRequests(accessToken, { force });
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!accessToken) return;
    const controller = new AbortController();
    void (async () => {
      setIsLoading(true);
      try {
        const response = await fetchITRequests(accessToken);
        if (controller.signal.aborted) return;
        setItems(response.items);
        setError(null);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load requests");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    })();
    return () => controller.abort();
  }, [accessToken]);

  if (!accessToken) return null;

  return (
    <ITRequestListPage
      title="IT Requests"
      description="Request approved software or access. Actions are simulated and never change this machine."
      basePath="/app/employee/it-requests"
      accessToken={accessToken}
      items={items}
      isLoading={isLoading}
      error={error}
      canCreate
      onCreated={() => reload(true)}
    />
  );
}
