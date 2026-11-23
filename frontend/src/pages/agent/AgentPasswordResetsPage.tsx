import { useEffect, useState } from "react";

import PasswordResetList from "../../components/passwordReset/PasswordResetList";
import { useAuth } from "../../context/AuthContext";
import { fetchPasswordResets } from "../../lib/passwordResets";
import type { PasswordResetListItem } from "../../lib/passwordResets.types";

export default function AgentPasswordResetsPage() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<PasswordResetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      title="Password Resets"
      description="Review escalated and in-progress password reset requests."
      basePath="/app/agent/password-resets"
      accessToken={accessToken}
      items={items}
      isLoading={isLoading}
      error={error}
    />
  );
}
