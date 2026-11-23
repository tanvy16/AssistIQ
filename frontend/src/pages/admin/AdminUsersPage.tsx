import { FormEvent, useCallback, useEffect, useState } from "react";

import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import DataUnavailable from "../../components/ui/DataUnavailable";
import EmptyState from "../../components/ui/EmptyState";
import Input from "../../components/ui/Input";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useToast } from "../../components/ui/Toast";
import { useAuth } from "../../context/AuthContext";
import { roleLabels } from "../../lib/labels";
import { adminResetUserMfa } from "../../lib/security";
import { fetchUsers, type DirectoryUser } from "../../lib/users";

export default function AdminUsersPage() {
  const { accessToken, user: me } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState<DirectoryUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [resetTarget, setResetTarget] = useState<DirectoryUser | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!accessToken) return;
      setIsLoading(true);
      try {
        const response = await fetchUsers(accessToken, signal);
        if (signal?.aborted) return;
        setUsers(response.items);
        setError(null);
      } catch (err) {
        if (signal?.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load users");
      } finally {
        if (!signal?.aborted) setIsLoading(false);
      }
    },
    [accessToken],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const enrolledPrivileged = users?.filter((u) => u.mfa_required && u.mfa_enabled).length ?? 0;
  const totalPrivileged = users?.filter((u) => u.mfa_required).length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="AssistIQ accounts, roles and multi-factor authentication status."
      />

      {users ? (
        <p className="text-sm text-ink-muted">
          MFA coverage for roles that require it:{" "}
          <span className="font-medium text-ink">
            {enrolledPrivileged} of {totalPrivileged}
          </span>{" "}
          enrolled.
        </p>
      ) : null}

      {resetTarget && accessToken ? (
        <Panel title={`Reset MFA for ${resetTarget.email}`} description="Recovery when a user lost their authenticator and recovery codes">
          <ResetMfaForm
            onCancel={() => setResetTarget(null)}
            onSubmit={async (adminPassword) => {
              const result = await adminResetUserMfa(accessToken, resetTarget.id, adminPassword);
              showToast(
                `MFA removed for ${resetTarget.email}. ${result.revoked} session(s) signed out; they must enroll again.`,
                "success",
              );
              setResetTarget(null);
              void load();
            }}
          />
        </Panel>
      ) : null}

      <Panel>
        {isLoading && !users ? <LoadingState label="Loading users…" /> : null}
        {error && !users ? <DataUnavailable error={error} onRetry={() => void load()} subject="users" /> : null}
        {users && !users.length ? (
          <EmptyState title="No users found" description="No accounts are registered in this environment." />
        ) : null}
        {users?.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-surface-border text-sm">
              <thead className="bg-surface-muted">
                <tr>
                  {["Name", "Email", "Role", "Status", "MFA", ""].map((column, index) => (
                    <th
                      key={column || index}
                      className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-ink-muted"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-hover">
                    <td className="px-4 py-3 font-medium text-ink">{user.display_name || "—"}</td>
                    <td className="px-4 py-3 text-ink-muted">{user.email}</td>
                    <td className="px-4 py-3">
                      <Badge variant="muted">{roleLabels[user.role]}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={user.is_active ? "success" : "muted"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={user.mfa_enabled ? "success" : user.mfa_required ? "warning" : "muted"}>
                        {user.mfa_enabled ? "Enabled" : user.mfa_required ? "Required · not set" : "Off"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {user.mfa_enabled && user.id !== me?.id ? (
                        <Button variant="ghost" size="sm" onClick={() => setResetTarget(user)}>
                          Reset MFA
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}

function ResetMfaForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (adminPassword: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={handle}>
      <p className="text-sm text-ink-muted">
        Verify the user's identity out of band first. This removes their authenticator and recovery codes,
        signs out all their sessions, and is recorded in the audit log.
      </p>
      <Input
        label="Your admin password"
        id="admin-reset-password"
        type="password"
        autoComplete="current-password"
        revealable
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      {error ? <Alert>{error}</Alert> : null}
      <div className="flex gap-2">
        <Button type="submit" variant="danger" disabled={busy || !password}>
          {busy ? "Resetting…" : "Reset MFA"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
