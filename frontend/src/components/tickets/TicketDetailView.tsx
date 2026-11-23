import { FormEvent, useState } from "react";

import Alert from "../ui/Alert";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import Panel from "../ui/Panel";
import {
  categoryLabels,
  formatDateTime,
  formatEventLabel,
  statusLabels,
} from "../../lib/ticketLabels";
import type { TicketDetail, TicketStatus } from "../../lib/tickets.types";
import SlaBadge from "./SlaBadge";
import { TicketPriorityBadge, TicketStatusBadge } from "./TicketBadges";

type TicketDetailViewProps = {
  ticket: TicketDetail | null;
  isLoading: boolean;
  error: string | null;
  canManage: boolean;
  canComment: boolean;
  onAssign?: () => Promise<void>;
  onUnassign?: () => Promise<void>;
  onStatusChange?: (status: TicketStatus) => Promise<void>;
  onAddComment?: (body: string) => Promise<void>;
};

const agentStatuses: TicketStatus[] = [
  "in_progress",
  "pending",
  "resolved",
  "closed",
];

export default function TicketDetailView({
  ticket,
  isLoading,
  error,
  canManage,
  canComment,
  onAssign,
  onUnassign,
  onStatusChange,
  onAddComment,
}: TicketDetailViewProps) {
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Every ticket mutation goes through here: one action at a time (no double
  // submit) and failures are shown instead of being silently dropped.
  async function runAction(key: string, action: () => Promise<void>) {
    if (pendingAction) return;
    setPendingAction(key);
    setActionError(null);
    try {
      await action();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "The action failed. Nothing was changed.");
    } finally {
      setPendingAction(null);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading ticket…" />;
  }

  if (error) {
    return (
      <EmptyState
        title="Unable to load ticket"
        description={error}
      />
    );
  }

  if (!ticket) {
    return null;
  }

  async function handleCommentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onAddComment || !comment.trim()) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await onAddComment(comment.trim());
      setComment("");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Comment was not saved.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${ticket.ticket_number} — ${ticket.title}`}
        description={`Created ${formatDateTime(ticket.created_at)}`}
        actions={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              {!ticket.assignee && onAssign ? (
                <Button
                  size="sm"
                  disabled={pendingAction !== null}
                  onClick={() => void runAction("assign", onAssign)}
                >
                  {pendingAction === "assign" ? "Claiming…" : "Claim ticket"}
                </Button>
              ) : null}
              {ticket.assignee && onUnassign ? (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={pendingAction !== null}
                  onClick={() => void runAction("unassign", onUnassign)}
                >
                  {pendingAction === "unassign" ? "Unassigning…" : "Unassign"}
                </Button>
              ) : null}
            </div>
          ) : null
        }
      />

      {actionError ? <Alert>{actionError}</Alert> : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Ticket information" className="lg:col-span-2">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">Status</dt>
              <dd className="mt-1">
                <TicketStatusBadge status={ticket.status} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">Priority</dt>
              <dd className="mt-1">
                <TicketPriorityBadge priority={ticket.priority} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">Category</dt>
              <dd className="mt-1 text-sm text-ink">{categoryLabels[ticket.category]}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">SLA</dt>
              <dd className="mt-1">
                <SlaBadge dueAt={ticket.sla_due_at} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">Requester</dt>
              <dd className="mt-1 text-sm text-ink">
                {ticket.requester.display_name ?? ticket.requester.email}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">Assignee</dt>
              <dd className="mt-1 text-sm text-ink">
                {ticket.assignee
                  ? ticket.assignee.display_name ?? ticket.assignee.email
                  : "Unassigned"}
              </dd>
            </div>
          </dl>
          <div className="mt-4 border-t border-surface-border pt-4">
            <h3 className="text-sm font-medium text-ink">Description</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-muted">
              {ticket.description}
            </p>
          </div>
        </Panel>

        {canManage && onStatusChange && ticket.status !== "closed" ? (
          <Panel title="Status actions">
            <div className="flex flex-col gap-2">
              {agentStatuses
                .filter((status) => status !== ticket.status)
                .map((status) => (
                  <Button
                    key={status}
                    size="sm"
                    variant="secondary"
                    disabled={pendingAction !== null}
                    onClick={() => void runAction(status, () => onStatusChange(status))}
                  >
                    {pendingAction === status ? "Updating…" : `Mark ${statusLabels[status]}`}
                  </Button>
                ))}
            </div>
          </Panel>
        ) : (
          <Panel title="Status">
            <p className="text-sm text-ink-muted">
              Current status: {statusLabels[ticket.status]}
            </p>
          </Panel>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Activity timeline">
          {ticket.events.length === 0 ? (
            <EmptyState
              title="No activity yet"
              description="Ticket events will appear here."
            />
          ) : (
            <ol className="space-y-3">
              {ticket.events.map((event) => (
                <li
                  key={event.id}
                  className="rail-activity border border-surface-border bg-surface-muted px-3 py-2"
                >
                  <p className="text-sm font-medium text-ink">
                    {formatEventLabel(event.event_type)}
                  </p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {formatDateTime(event.created_at)}
                    {event.actor
                      ? ` · ${event.actor.display_name ?? event.actor.email}`
                      : ""}
                  </p>
                  {event.old_value || event.new_value ? (
                    <p className="mt-1 text-xs text-ink-muted">
                      {event.old_value ? `${event.old_value} → ` : ""}
                      {event.new_value ?? ""}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel title="Comments">
          {ticket.comments.length === 0 ? (
            <EmptyState
              title="No comments yet"
              description="Comments from requesters and agents will appear here."
            />
          ) : (
            <ul className="space-y-3">
              {ticket.comments.map((item) => (
                <li
                  key={item.id}
                  className="rounded border border-surface-border px-3 py-2"
                >
                  <p className="text-xs font-medium text-ink">
                    {item.author.display_name ?? item.author.email}
                  </p>
                  <p className="mt-1 text-sm text-ink-muted">{item.body}</p>
                  <p className="mt-1 text-xs text-ink-muted">
                    {formatDateTime(item.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}

          {canComment && onAddComment ? (
            <form className="mt-4 space-y-2 border-t border-surface-border pt-4" onSubmit={handleCommentSubmit}>
              <label htmlFor="comment-body" className="block text-sm font-medium text-ink">
                Add comment
              </label>
              <textarea
                id="comment-body"
                rows={3}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                className="field-control"
              />
              <Button type="submit" size="sm" disabled={submitting || !comment.trim()}>
                Post comment
              </Button>
            </form>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
