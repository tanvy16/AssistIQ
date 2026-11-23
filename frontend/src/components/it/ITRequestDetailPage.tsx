import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import Panel from "../ui/Panel";
import { useToast } from "../ui/Toast";
import {
  approveITRequest,
  cancelITRequest,
  fetchITRequest,
  fetchITRequestEvents,
  rejectITRequest,
  statusExplanation,
} from "../../lib/itRequests";
import type { ITRequestDetail, ITRequestEvent } from "../../lib/itRequests.types";

type ITRequestDetailPageProps = {
  accessToken: string;
  listPath: string;
  canApprove?: boolean;
  canCancel?: boolean;
};

export default function ITRequestDetailPage({
  accessToken,
  listPath,
  canApprove = false,
  canCancel = false,
}: ITRequestDetailPageProps) {
  const { requestId = "" } = useParams();
  const { showToast } = useToast();
  const [request, setRequest] = useState<ITRequestDetail | null>(null);
  const [events, setEvents] = useState<ITRequestEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setIsLoading(true);
    try {
      const [detail, timeline] = await Promise.all([
        fetchITRequest(accessToken, requestId),
        fetchITRequestEvents(accessToken, requestId),
      ]);
      setRequest(detail);
      setEvents(timeline);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load request");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!accessToken || !requestId) return;
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, requestId]);

  const execution = request?.executions[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="IT request"
        description="Policy-controlled software and access workflow. Execution is simulated in this phase."
        actions={
          <Link to={listPath}>
            <Button variant="secondary">Back to list</Button>
          </Link>
        }
      />

      {isLoading ? <LoadingState label="Loading request…" /> : null}
      {!isLoading && error ? <EmptyState title="Unable to load request" description={error} /> : null}

      {request ? (
        <>
          <Panel title={request.requested_resource}>
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge>{request.request_type}</Badge>
              <Badge
                variant={
                  request.status === "completed"
                    ? "success"
                    : request.status === "rejected" || request.status === "escalated"
                      ? "danger"
                      : request.status === "executing"
                        ? "activity"
                        : "muted"
                }
              >
                {request.status}
              </Badge>
              <Badge variant={request.risk_level === "high" ? "danger" : request.risk_level === "medium" ? "warning" : "muted"}>
                {request.risk_level} risk
              </Badge>
            </div>
            <p className="text-sm text-ink">{statusExplanation(request.status)}</p>
            <p className="mt-3 text-sm text-ink-muted">Original request: {request.user_message}</p>
            {request.justification ? (
              <p className="mt-1 text-sm text-ink-muted">Justification: {request.justification}</p>
            ) : null}
            {request.approval_required ? (
              <p className="mt-3 text-sm text-ink">Approval is required before a simulated action can run.</p>
            ) : null}
            {request.plan ? (
              <p className="mt-3 text-sm text-ink-muted">
                Planned runbook: {String(request.selected_runbook_id)} (allow-listed, simulated)
              </p>
            ) : null}

            {canApprove && request.status === "approval_required" ? (
              <div className="mt-4 flex gap-2">
                <Button
                  onClick={async () => {
                    try {
                      const updated = await approveITRequest(accessToken, request.id);
                      const status = (updated as { status?: string }).status ?? "";
                      if (status === "completed") {
                        showToast("Approved. Simulated execution completed — nothing was installed or changed.", "success");
                      } else if (status === "failed" || status === "rolled_back") {
                        showToast(`Approved, but the simulated execution ${status.replace(/_/g, " ")}.`, "error");
                      } else {
                        showToast(`Approved. Request status: ${status.replace(/_/g, " ") || "updated"}.`, "info");
                      }
                      await reload();
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Approve failed", "error");
                    }
                  }}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  onClick={async () => {
                    try {
                      await rejectITRequest(accessToken, request.id);
                      showToast("Request rejected.", "success");
                      await reload();
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Reject failed", "error");
                    }
                  }}
                >
                  Reject
                </Button>
              </div>
            ) : null}

            {canCancel && request.status === "approval_required" ? (
              <div className="mt-4">
                <Button
                  variant="secondary"
                  onClick={async () => {
                    try {
                      await cancelITRequest(accessToken, request.id);
                      showToast("Request cancelled.", "success");
                      await reload();
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Cancel failed", "error");
                    }
                  }}
                >
                  Cancel request
                </Button>
              </div>
            ) : null}
          </Panel>

          <Panel title="Extracted entities">
            {request.entities.length === 0 ? (
              <p className="text-sm text-ink-muted">No structured entities extracted.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {request.entities.map((entity) => (
                  <li key={entity.id}>
                    <span className="font-medium">{entity.entity_type}:</span> {entity.entity_value}
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Execution" description="Mock adapter only — no host or IAM changes." className="rail-activity">
            {execution ? (
              <div className="space-y-2 text-sm">
                <p>Status: {execution.status}</p>
                <p>Adapter: {execution.adapter_name}</p>
                <p>{String(execution.execution_result?.message ?? "No execution message")}</p>
                {execution.validation_result ? (
                  <p>Validation: {String((execution.validation_result as { passed?: boolean }).passed ? "passed" : "failed")}</p>
                ) : null}
                {execution.rollback_status ? <p>Rollback: {execution.rollback_status}</p> : null}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">No execution has been recorded yet.</p>
            )}
          </Panel>

          <Panel title="Timeline">
            <ol className="space-y-2 text-sm">
              {events.map((event) => (
                <li key={event.id} className="rail-activity pl-3">
                  <span className="font-medium">{event.event_type}</span>
                  <span className="text-ink-muted"> · {new Date(event.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ol>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
