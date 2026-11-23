import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Input from "../ui/Input";
import LoadingState from "../ui/LoadingState";
import PageHeader from "../ui/PageHeader";
import Panel from "../ui/Panel";
import { useToast } from "../ui/Toast";
import {
  confirmPasswordReset,
  escalatePasswordReset,
  fetchPasswordReset,
  passwordResetStatusCopy,
  rejectPasswordReset,
  verifyPasswordReset,
} from "../../lib/passwordResets";
import type { PasswordResetDetail } from "../../lib/passwordResets.types";

type PasswordResetDetailViewProps = {
  accessToken: string;
  listPath: string;
  canVerify?: boolean;
  canConfirm?: boolean;
  canEscalate?: boolean;
  canReject?: boolean;
};

export default function PasswordResetDetailView({
  accessToken,
  listPath,
  canVerify = false,
  canConfirm = false,
  canEscalate = false,
  canReject = false,
}: PasswordResetDetailViewProps) {
  const { requestId = "" } = useParams();
  const { showToast } = useToast();
  const [request, setRequest] = useState<PasswordResetDetail | null>(null);
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setIsLoading(true);
    try {
      setRequest(await fetchPasswordReset(accessToken, requestId));
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

  async function handleVerify(event: FormEvent) {
    event.preventDefault();
    try {
      const updated = await verifyPasswordReset(accessToken, requestId, email);
      setRequest(updated);
      showToast("Verification submitted.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Verification failed", "error");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Password reset"
        description="Policy-controlled identity verification. Execution is simulated in this phase."
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
          <Panel title="Request status">
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge
                variant={
                  request.status === "completed"
                    ? "success"
                    : request.status === "rejected" || request.status.includes("fail")
                      ? "danger"
                      : "muted"
                }
              >
                {request.status.replace(/_/g, " ")}
              </Badge>
              <Badge variant={request.risk_level === "high" ? "danger" : request.risk_level === "medium" ? "warning" : "muted"}>
                {request.risk_level} risk
              </Badge>
              <Badge variant="muted">{request.verification_status}</Badge>
            </div>
            <p className="text-sm text-ink">{passwordResetStatusCopy(request.status)}</p>
            {request.reason ? <p className="mt-2 text-sm text-ink-muted">{request.reason}</p> : null}
          </Panel>

          {canVerify && ["verification_required", "verification_failed"].includes(request.status) ? (
            <Panel title="Identity verification">
              <form onSubmit={(event) => void handleVerify(event)} className="space-y-3">
                <Input
                  label="Registered email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
                <Button type="submit" disabled={!email.trim()}>
                  Verify identity
                </Button>
              </form>
            </Panel>
          ) : null}

          {canConfirm && request.status === "confirmation_required" ? (
            <Panel title="Confirmation">
              <p className="mb-3 text-sm text-ink">
                You are requesting a password reset for your account. After confirmation, a simulated reset will run.
                Your real password will not change.
              </p>
              <Button
                onClick={async () => {
                  try {
                    const updated = await confirmPasswordReset(accessToken, request.id);
                    setRequest(updated);
                    // Report what the server actually returned, never a blanket success.
                    if (updated.status === "completed") {
                      showToast("Simulated reset completed. Your real password was not changed.", "success");
                    } else if (updated.status === "failed" || updated.status === "rejected") {
                      showToast(`Simulated reset did not complete (status: ${updated.status}).`, "error");
                    } else {
                      showToast(`Request is now ${updated.status.replace(/_/g, " ")}.`, "info");
                    }
                  } catch (err) {
                    showToast(err instanceof Error ? err.message : "Confirm failed", "error");
                  }
                }}
              >
                Confirm simulated reset
              </Button>
            </Panel>
          ) : null}

          {request.execution_result ? (
            <Panel title="Execution" description="Mock IAM adapter only.">
              <p className="text-sm text-ink">{String(request.execution_result.message ?? "")}</p>
            </Panel>
          ) : null}

          <div className="flex gap-2">
            {canEscalate && request.status !== "completed" && request.status !== "rejected" ? (
              <Button
                variant="secondary"
                onClick={async () => {
                  try {
                    setRequest(await escalatePasswordReset(accessToken, request.id));
                    showToast("Request escalated.", "success");
                  } catch (err) {
                    showToast(err instanceof Error ? err.message : "Escalate failed", "error");
                  }
                }}
              >
                Escalate
              </Button>
            ) : null}
            {canReject && request.status !== "completed" ? (
              <Button
                variant="danger"
                onClick={async () => {
                  try {
                    setRequest(await rejectPasswordReset(accessToken, request.id));
                    showToast("Request rejected.", "success");
                  } catch (err) {
                    showToast(err instanceof Error ? err.message : "Reject failed", "error");
                  }
                }}
              >
                Reject
              </Button>
            ) : null}
          </div>

          <Panel title="Timeline">
            <ol className="space-y-2 text-sm">
              {request.events.map((event) => (
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
