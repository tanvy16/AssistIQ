import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import Panel from "../ui/Panel";
import { useToast } from "../ui/Toast";
import { createPasswordReset } from "../../lib/passwordResets";
import type { PasswordResetListItem } from "../../lib/passwordResets.types";

type PasswordResetListProps = {
  title: string;
  description: string;
  basePath: string;
  accessToken: string;
  items: PasswordResetListItem[];
  isLoading: boolean;
  error: string | null;
  canCreate?: boolean;
  onCreated?: () => Promise<void>;
};

export default function PasswordResetList({
  title,
  description,
  basePath,
  accessToken,
  items,
  isLoading,
  error,
  canCreate = false,
  onCreated,
}: PasswordResetListProps) {
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await createPasswordReset(accessToken, "I need a password reset for my account");
      showToast("Password reset request created. Verify your identity next.", "success");
      await onCreated?.();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Could not create request", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} />
      {canCreate ? (
        <Panel title="New request" description="Identity verification is required. This never changes a real password.">
          <form onSubmit={(event) => void handleCreate(event)}>
            <Button type="submit" disabled={isSubmitting}>
              Start password reset
            </Button>
          </form>
        </Panel>
      ) : null}
      {isLoading ? <LoadingState label="Loading password reset requests…" /> : null}
      {!isLoading && error ? <EmptyState title="Unable to load requests" description={error} /> : null}
      {!isLoading && !error && items.length === 0 ? (
        <EmptyState title="No password reset requests" description="Submitted requests will appear here." />
      ) : null}
      {!isLoading && !error && items.length > 0 ? (
        <Panel title="Requests">
          <ul className="divide-y divide-surface-border">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                <Link to={`${basePath}/${item.id}`} className="font-medium text-ink hover:underline">
                  {item.id.slice(0, 8)} · {item.status.replace(/_/g, " ")}
                </Link>
                <Badge
                  variant={
                    item.status === "completed"
                      ? "success"
                      : item.status === "rejected" || item.status.includes("fail")
                        ? "danger"
                        : "muted"
                  }
                >
                  {item.status}
                </Badge>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}
