import { FormEvent, useCallback, useEffect, useState } from "react";

import MfaEnrollment from "../components/security/MfaEnrollment";
import RecoveryCodes from "../components/security/RecoveryCodes";
import Alert from "../components/ui/Alert";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import DataUnavailable from "../components/ui/DataUnavailable";
import Input from "../components/ui/Input";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import { useToast } from "../components/ui/Toast";
import { useAuth } from "../context/AuthContext";
import {
  changePassword,
  disableMfa,
  fetchMfaStatus,
  fetchSessions,
  passwordPolicyProblem,
  regenerateRecoveryCodes,
  revokeOtherSessions,
  type MfaStatus,
  type SessionInfo,
} from "../lib/security";
import { formatDateTime } from "../lib/ticketLabels";

type MfaMode = "idle" | "enroll" | "regenerate" | "disable";

function describeAgent(userAgent: string | null): string {
  if (!userAgent) return "Unknown client";
  const browser = /Edg\//.test(userAgent)
    ? "Edge"
    : /Chrome\//.test(userAgent)
      ? "Chrome"
      : /Firefox\//.test(userAgent)
        ? "Firefox"
        : /Safari\//.test(userAgent)
          ? "Safari"
          : "Browser / API client";
  const os = /Windows/.test(userAgent)
    ? "Windows"
    : /Mac OS/.test(userAgent)
      ? "macOS"
      : /Android/.test(userAgent)
        ? "Android"
        : /iPhone|iPad/.test(userAgent)
          ? "iOS"
          : /Linux/.test(userAgent)
            ? "Linux"
            : "";
  return os ? `${browser} on ${os}` : browser;
}

export default function SecurityPage() {
  const { user, accessToken, applySession } = useAuth();
  const { showToast } = useToast();
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [mode, setMode] = useState<MfaMode>("idle");
  const [newCodes, setNewCodes] = useState<string[] | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!accessToken) return;
      const [mfaResult, sessionResult] = await Promise.allSettled([
        fetchMfaStatus(accessToken, signal),
        fetchSessions(accessToken, signal),
      ]);
      if (signal?.aborted) return;
      if (mfaResult.status === "fulfilled") {
        setStatus(mfaResult.value);
        setStatusError(null);
      } else {
        setStatusError(mfaResult.reason instanceof Error ? mfaResult.reason.message : "Request failed");
      }
      if (sessionResult.status === "fulfilled") {
        setSessions(sessionResult.value.items);
        setSessionsError(null);
      } else {
        setSessionsError(
          sessionResult.reason instanceof Error ? sessionResult.reason.message : "Request failed",
        );
      }
    },
    [accessToken],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (!user || !accessToken) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security"
        description="Two-step sign-in, recovery codes, password and active sessions for your account."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel
          title="Two-step sign-in (TOTP)"
          description="Authenticator-app codes required at every sign-in"
          className="lg:col-span-2"
        >
          {!status && !statusError ? <LoadingState label="Loading MFA status…" /> : null}
          {statusError && !status ? (
            <DataUnavailable error={statusError} onRetry={() => void load()} subject="MFA status" />
          ) : null}

          {status ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={status.enabled ? "success" : status.required_for_role ? "danger" : "muted"}>
                  {status.enabled ? "Enabled" : "Not enabled"}
                </Badge>
                {status.required_for_role ? (
                  <Badge variant="muted">
                    Required for {user.role} · {status.enforcement_mode === "strict" ? "enforced" : "grace period"}
                  </Badge>
                ) : (
                  <Badge variant="muted">Optional for your role</Badge>
                )}
                {status.enabled_at ? (
                  <span className="text-xs text-ink-muted">since {formatDateTime(status.enabled_at)}</span>
                ) : null}
              </div>

              {status.locked_until && new Date(status.locked_until) > new Date() ? (
                <Alert>
                  Code entry is locked after repeated incorrect codes until {formatDateTime(status.locked_until)}.
                </Alert>
              ) : null}

              {newCodes ? (
                <RecoveryCodes
                  email={user.email}
                  codes={newCodes}
                  onDone={() => {
                    setNewCodes(null);
                    void load();
                  }}
                  doneLabel="Done"
                />
              ) : null}

              {!newCodes && mode === "enroll" ? (
                <MfaEnrollment
                  token={accessToken}
                  email={user.email}
                  onCancel={() => setMode("idle")}
                  onComplete={(session) => {
                    if (session) applySession(session.accessToken, session.user);
                    setMode("idle");
                    showToast("Two-step sign-in enabled. Other sessions were signed out.", "success");
                    void load();
                  }}
                />
              ) : null}

              {!newCodes && mode === "regenerate" ? (
                <ReauthForm
                  submitLabel="Generate new codes"
                  description="Old recovery codes stop working immediately."
                  needsFactorChoice={false}
                  onCancel={() => setMode("idle")}
                  onSubmit={async (password, factor) => {
                    const result = await regenerateRecoveryCodes(accessToken, password, factor.value);
                    setMode("idle");
                    setNewCodes(result.recovery_codes);
                  }}
                />
              ) : null}

              {!newCodes && mode === "disable" ? (
                <ReauthForm
                  submitLabel="Disable two-step sign-in"
                  description="Your account will be protected by your password only."
                  needsFactorChoice
                  danger
                  onCancel={() => setMode("idle")}
                  onSubmit={async (password, factor) => {
                    await disableMfa(
                      accessToken,
                      password,
                      factor.kind === "recovery" ? { recovery_code: factor.value } : { code: factor.value },
                    );
                    setMode("idle");
                    showToast("Two-step sign-in disabled.", "info");
                    applySession(accessToken, { ...user, mfa_enabled: false });
                    void load();
                  }}
                />
              ) : null}

              {!newCodes && mode === "idle" ? (
                status.enabled ? (
                  <div className="space-y-3">
                    <p className="text-sm text-ink-muted">
                      Recovery codes remaining:{" "}
                      <span className={status.recovery_codes_remaining <= 2 ? "font-semibold text-danger" : "font-semibold text-ink"}>
                        {status.recovery_codes_remaining}
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" size="sm" onClick={() => setMode("regenerate")}>
                        Regenerate recovery codes
                      </Button>
                      {!(status.required_for_role && status.enforcement_mode === "strict") ? (
                        <Button variant="secondary" size="sm" onClick={() => setMode("disable")}>
                          Disable
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-ink-muted">
                      Add a second step to sign-in using Google Authenticator, Microsoft Authenticator or any
                      TOTP app. You'll receive one-time recovery codes in case you lose your device.
                    </p>
                    <Button onClick={() => setMode("enroll")}>Set up authenticator</Button>
                  </div>
                )
              ) : null}
            </div>
          ) : null}
        </Panel>

        <Panel title="Change password" description="Signs out your other sessions">
          <ChangePasswordForm
            mfaEnabled={Boolean(status?.enabled)}
            onSubmit={async (current, next, code) => {
              const result = await changePassword(accessToken, current, next, code);
              showToast(
                `Password changed. ${result.revoked} other session${result.revoked === 1 ? "" : "s"} signed out.`,
                "success",
              );
              void load();
            }}
          />
        </Panel>
      </div>

      <Panel title="Active sessions" description="Devices holding a valid refresh token for your account">
        {!sessions && !sessionsError ? <LoadingState label="Loading sessions…" /> : null}
        {sessionsError && !sessions ? (
          <DataUnavailable error={sessionsError} onRetry={() => void load()} subject="sessions" />
        ) : null}
        {sessions ? (
          <div className="space-y-3">
            <ul className="divide-y divide-surface-border">
              {sessions.map((session) => (
                <li key={session.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 first:pt-0">
                  <div>
                    <p className="text-sm text-ink">
                      {describeAgent(session.user_agent)}
                      {session.current ? <span className="ml-2 text-xs text-accent">This session</span> : null}
                    </p>
                    <p className="text-xs text-ink-muted">
                      Signed in {formatDateTime(session.created_at)} · expires {formatDateTime(session.expires_at)}
                    </p>
                  </div>
                  <Badge variant={session.mfa_verified ? "success" : "muted"}>
                    {session.mfa_verified ? "MFA verified" : "Password only"}
                  </Badge>
                </li>
              ))}
            </ul>
            {sessions.length === 0 ? (
              <p className="text-sm text-ink-muted">No active refresh sessions were found.</p>
            ) : null}
            <Button
              variant="secondary"
              size="sm"
              disabled={sessions.filter((s) => !s.current).length === 0}
              onClick={async () => {
                try {
                  const result = await revokeOtherSessions(accessToken);
                  showToast(`${result.revoked} other session${result.revoked === 1 ? "" : "s"} signed out.`, "success");
                  void load();
                } catch (err) {
                  showToast(err instanceof Error ? err.message : "Could not sign out other sessions", "error");
                }
              }}
            >
              Sign out other sessions
            </Button>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}

type Factor = { kind: "totp" | "recovery"; value: string };

function ReauthForm({
  submitLabel,
  description,
  needsFactorChoice,
  danger = false,
  onSubmit,
  onCancel,
}: {
  submitLabel: string;
  description: string;
  needsFactorChoice: boolean;
  danger?: boolean;
  onSubmit: (password: string, factor: Factor) => Promise<void>;
  onCancel: () => void;
}) {
  const [password, setPassword] = useState("");
  const [value, setValue] = useState("");
  const [kind, setKind] = useState<Factor["kind"]>("totp");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(password, { kind, value: value.trim() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setValue("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={handle}>
      <p className="text-sm text-ink-muted">{description} Confirm your password and a current code.</p>
      <Input
        label="Current password"
        id="reauth-password"
        type="password"
        autoComplete="current-password"
        revealable
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <Input
        label={kind === "recovery" ? "Recovery code" : "Authenticator code"}
        id="reauth-code"
        autoComplete="one-time-code"
        inputMode={kind === "recovery" ? "text" : "numeric"}
        maxLength={kind === "recovery" ? 24 : 8}
        required
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      {needsFactorChoice ? (
        <button
          type="button"
          className="text-sm text-accent hover:underline"
          onClick={() => {
            setKind((current) => (current === "totp" ? "recovery" : "totp"));
            setValue("");
          }}
        >
          {kind === "totp" ? "Use a recovery code instead" : "Use authenticator code instead"}
        </button>
      ) : null}
      {error ? <Alert>{error}</Alert> : null}
      <div className="flex gap-2">
        <Button type="submit" variant={danger ? "danger" : "primary"} disabled={busy || !password || value.trim().length < 6}>
          {busy ? "Working…" : submitLabel}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function ChangePasswordForm({
  mfaEnabled,
  onSubmit,
}: {
  mfaEnabled: boolean;
  onSubmit: (current: string, next: string, code?: string) => Promise<void>;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const policyProblem = next ? passwordPolicyProblem(next) : null;
  const mismatch = confirm.length > 0 && confirm !== next;

  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (policyProblem || mismatch) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit(current, next, mfaEnabled ? code.trim() : undefined);
      setCurrent("");
      setNext("");
      setConfirm("");
      setCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password was not changed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={handle}>
      <Input label="Current password" id="pw-current" type="password" autoComplete="current-password" revealable required value={current} onChange={(e) => setCurrent(e.target.value)} />
      <Input
        label="New password"
        id="pw-new"
        type="password"
        autoComplete="new-password"
        revealable
        required
        maxLength={72}
        hint="12+ characters, mixing three of: lowercase, uppercase, digits, symbols."
        error={policyProblem ?? undefined}
        value={next}
        onChange={(e) => setNext(e.target.value)}
      />
      <Input label="Confirm new password" id="pw-confirm" type="password" autoComplete="new-password" required error={mismatch ? "Passwords do not match." : undefined} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      {mfaEnabled ? (
        <Input label="Authenticator code" id="pw-code" inputMode="numeric" autoComplete="one-time-code" maxLength={8} required value={code} onChange={(e) => setCode(e.target.value)} />
      ) : null}
      {error ? <Alert>{error}</Alert> : null}
      <Button type="submit" disabled={busy || !current || !next || Boolean(policyProblem) || mismatch || confirm !== next}>
        {busy ? "Changing…" : "Change password"}
      </Button>
    </form>
  );
}
