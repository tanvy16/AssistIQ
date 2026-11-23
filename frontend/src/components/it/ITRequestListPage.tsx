import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Input from "../ui/Input";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import Panel from "../ui/Panel";
import { useToast } from "../ui/Toast";
import { createITRequest } from "../../lib/itRequests";
import type { ITRequestListItem } from "../../lib/itRequests.types";

type ITRequestListPageProps = {
  title: string;
  description: string;
  basePath: string;
  accessToken: string;
  items: ITRequestListItem[];
  isLoading: boolean;
  error: string | null;
  canCreate?: boolean;
  onCreated?: () => Promise<void>;
};

export default function ITRequestListPage({
  title,
  description,
  basePath,
  accessToken,
  items,
  isLoading,
  error,
  canCreate = false,
  onCreated,
}: ITRequestListPageProps) {
  const { showToast } = useToast();
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    setIsSubmitting(true);
    try {
      await createITRequest(accessToken, message.trim());
      setMessage("");
      showToast("IT request submitted.", "success");
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
        <Panel title="New request" description="Catalog software and access requests only. Actions are simulated.">
          <form onSubmit={(event) => void handleCreate(event)} className="space-y-3">
            <Input
              label="What do you need?"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="I need Visual Studio Code installed for backend development"
              disabled={isSubmitting}
            />
            <Button type="submit" disabled={isSubmitting || !message.trim()}>
              Submit request
            </Button>
          </form>
        </Panel>
      ) : null}

      {isLoading ? <LoadingState label="Loading IT requests…" /> : null}
      {!isLoading && error ? <EmptyState title="Unable to load requests" description={error} /> : null}
      {!isLoading && !error && items.length === 0 ? (
        <EmptyState title="No IT requests" description="Submitted software and access requests will appear here." />
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <Panel title="Requests">
          <ul className="divide-y divide-surface-border">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                <div>
                  <Link to={`${basePath}/${item.id}`} className="font-medium text-ink hover:underline">
                    {item.requested_resource}
                  </Link>
                  <p className="text-xs text-ink-muted">
                    {item.request_type} · {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={item.status === "completed" ? "success" : item.status === "rejected" || item.status === "escalated" ? "danger" : "muted"}>{item.status}</Badge>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}
