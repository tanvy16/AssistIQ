import { FormEvent, useState } from "react";

import type { UserPublic } from "../../lib/api";
import { startMfaEnrollment, verifyMfaEnrollment, type MfaEnrollStart } from "../../lib/security";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Input from "../ui/Input";
import RecoveryCodes from "./RecoveryCodes";

type MfaEnrollmentProps = {
  /** Access token, or the strict-mode enrollment token issued at sign-in. */
  token: string;
  email: string;
  /** Called after the user has saved their codes, with the upgraded session. */
  onComplete: (session: { accessToken: string; user: UserPublic } | null) => void;
  onCancel?: () => void;
};

type Step = "password" | "scan" | "codes";

export default function MfaEnrollment({ token, email, onComplete, onCancel }: MfaEnrollmentProps) {
  const [step, setStep] = useState<Step>("password");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [enrollment, setEnrollment] = useState<MfaEnrollStart | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [session, setSession] = useState<{ accessToken: string; user: UserPublic } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const started = await startMfaEnrollment(token, password);
      setPassword("");
      setEnrollment(started);
      setStep("scan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start enrollment");
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await verifyMfaEnrollment(token, code.trim());
      setCodes(result.recovery_codes);
      if (result.access_token && result.user) {
        setSession({ accessToken: result.access_token, user: result.user });
      }
      // The secret is no longer needed client-side once MFA is active.
      setEnrollment(null);
      setStep("codes");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  if (step === "codes") {
    return (
      <div className="space-y-3">
        <Alert tone="success">Multi-factor authentication is now enabled for {email}.</Alert>
        <RecoveryCodes email={email} codes={codes} onDone={() => onComplete(session)} doneLabel="Finish setup" />
      </div>
    );
  }

  if (step === "scan" && enrollment) {
    return (
      <form className="space-y-4" onSubmit={handleVerify}>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-ink-muted">
          <li>Open Google Authenticator, Microsoft Authenticator or another TOTP app.</li>
          <li>Scan the QR code (or enter the setup key manually).</li>
          <li>Enter the 6-digit code it shows. MFA is not enabled until this code is verified.</li>
        </ol>
        <div className="flex flex-col items-start gap-4 sm:flex-row">
          <img
            src={enrollment.qr_svg_data_uri}
            alt="QR code for adding AssistIQ to an authenticator app"
            className="h-44 w-44 rounded border border-surface-border bg-white p-1"
          />
          <div className="min-w-0 space-y-2 text-sm">
            <p className="text-ink-muted">Can't scan?</p>
            {showSecret ? (
              <code className="block break-all rounded border border-surface-border bg-surface-muted px-2 py-1 font-mono text-xs text-ink">
                {enrollment.secret.match(/.{1,4}/g)?.join(" ")}
              </code>
            ) : (
              <Button type="button" variant="secondary" size="sm" onClick={() => setShowSecret(true)}>
                Show setup key
              </Button>
            )}
            <p className="text-xs text-ink-subtle">Time-based · SHA-1 · 6 digits · 30 s</p>
          </div>
        </div>
        <Input
          label="Verification code"
          id="mfa-enroll-code"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9 ]{6,8}"
          maxLength={8}
          required
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
        {error ? <Alert>{error}</Alert> : null}
        <div className="flex gap-2">
          <Button type="submit" disabled={busy || code.trim().length < 6}>
            {busy ? "Verifying…" : "Verify and enable"}
          </Button>
          {onCancel ? (
            <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
              Cancel
            </Button>
          ) : null}
        </div>
      </form>
    );
  }

  return (
    <form className="space-y-4" onSubmit={handleStart}>
      <p className="text-sm text-ink-muted">Confirm your password to set up an authenticator app.</p>
      <Input
        label="Current password"
        id="mfa-enroll-password"
        type="password"
        autoComplete="current-password"
        revealable
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      {error ? <Alert>{error}</Alert> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={busy || !password}>
          {busy ? "Preparing…" : "Continue"}
        </Button>
        {onCancel ? (
          <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}
