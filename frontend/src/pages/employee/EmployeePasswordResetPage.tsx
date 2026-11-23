import { useEffect, useState } from "react";

import PasswordResetList from "../../components/passwordReset/PasswordResetList";
import { useAuth } from "../../context/AuthContext";
import { fetchPasswordResets } from "../../lib/passwordResets";
import type { PasswordResetListItem } from "../../lib/passwordResets.types";

export default function EmployeePasswordResetPage() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<PasswordResetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload(force = false) {
    if (!accessToken) return;
    setIsLoading(true);
    try {
      const response = await fetchPasswordResets(accessToken, { force });
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
        const response = await fetchPasswordResets(accessToken);
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
    <PasswordResetList
      title="Password Reset"
      description="Verify your identity, then confirm a simulated reset. Your real password will not change."
      basePath="/app/employee/password-reset"
      accessToken={accessToken}
      items={items}
      isLoading={isLoading}
      error={error}
      canCreate
      onCreated={() => reload(true)}
    />
  );
}
