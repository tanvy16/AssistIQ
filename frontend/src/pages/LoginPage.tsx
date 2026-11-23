import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";

import LoginBrandPanel from "../components/auth/LoginBrandPanel";
import MfaEnrollment from "../components/security/MfaEnrollment";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import ThemeToggle from "../components/ui/ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { getRoleHomePath } from "../lib/routes";

type Step =
  | { kind: "credentials" }
  | { kind: "mfa"; mfaToken: string }
  | { kind: "enroll"; enrollmentToken: string };

export default function LoginPage() {
  const { user, isLoading, login, completeMfa, applySession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<Step>({ kind: "credentials" });
  const [code, setCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && user) {
    return <Navigate to={getRoleHomePath(user.role)} replace />;
  }

  function backToCredentials(message?: string) {
    setStep({ kind: "credentials" });
    setCode("");
    setUseRecovery(false);
    setError(message ?? null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const outcome = await login(email, password);
      // The password is not needed past the first step.
      setPassword("");
      if (outcome.kind === "mfa_required") setStep({ kind: "mfa", mfaToken: outcome.mfaToken });
      if (outcome.kind === "enrollment_required") {
        setStep({ kind: "enroll", enrollmentToken: outcome.enrollmentToken });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step.kind !== "mfa") return;
    setError(null);
    setSubmitting(true);
    try {
      await completeMfa(
        step.mfaToken,
        useRecovery ? { recovery_code: code.trim() } : { code: code.replace(/\s/g, "") },
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Verification failed";
      if (message.toLowerCase().includes("expired")) backToCredentials(message);
      else setError(message);
      setCode("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[minmax(0,1.35fr)_minmax(24rem,28rem)]">
      <LoginBrandPanel />

      <section
        className="relative flex min-h-[70vh] items-center justify-center border-t border-surface-border px-6 py-12 lg:min-h-screen lg:border-l lg:border-t-0"
        style={{ backgroundColor: "var(--color-login-panel)" }}
      >
        <div className="absolute right-4 top-4 sm:right-6 sm:top-6">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-[26rem]">
          {step.kind === "credentials" ? (
            <>
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-subtle">
                Welcome back
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">Sign in to AssistIQ</h2>
              <p className="mt-2 text-sm text-ink-muted">
                Access your workspace and continue where you left off.
              </p>

              <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
                <Input
                  label="Email"
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />

                <Input
                  label="Password"
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  minLength={8}
                  maxLength={128}
                  revealable
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />

                {error ? <Alert>{error}</Alert> : null}

                <Button type="submit" disabled={submitting} className="h-11 w-full">
                  {submitting ? "Signing in…" : "Sign in"}
                </Button>
              </form>
            </>
          ) : null}

          {step.kind === "mfa" ? (
            <>
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-subtle">
                Step 2 of 2
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">Verify it's you</h2>
              <p className="mt-2 text-sm text-ink-muted">
                {useRecovery
                  ? "Enter one of your one-time recovery codes. Each code works once."
                  : "Enter the 6-digit code from your authenticator app."}
              </p>
              <form className="mt-8 space-y-4" onSubmit={handleMfa}>
                <Input
                  label={useRecovery ? "Recovery code" : "Authentication code"}
                  id="mfa-code"
                  autoFocus
                  required
                  autoComplete="one-time-code"
                  inputMode={useRecovery ? "text" : "numeric"}
                  maxLength={useRecovery ? 24 : 8}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
                {error ? <Alert>{error}</Alert> : null}
                <Button type="submit" disabled={submitting || code.trim().length < 6} className="h-11 w-full">
                  {submitting ? "Verifying…" : "Verify"}
                </Button>
              </form>
              <div className="mt-4 flex flex-wrap justify-between gap-2 text-sm">
                <button
                  type="button"
                  className="text-accent hover:underline"
                  onClick={() => {
                    setUseRecovery((current) => !current);
                    setCode("");
                    setError(null);
                  }}
                >
                  {useRecovery ? "Use authenticator code instead" : "Lost your device? Use a recovery code"}
                </button>
                <button type="button" className="text-ink-muted hover:text-ink" onClick={() => backToCredentials()}>
                  Back
                </button>
              </div>
              <p className="mt-6 text-xs text-ink-subtle">
                Lost both your device and recovery codes? An administrator can reset MFA for your account
                after verifying your identity.
              </p>
            </>
          ) : null}

          {step.kind === "enroll" ? (
            <>
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-subtle">
                Required for your role
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">Set up two-step sign-in</h2>
              <p className="mt-2 mb-6 text-sm text-ink-muted">
                Your organisation requires an authenticator app for this account before you can continue.
              </p>
              <MfaEnrollment
                token={step.enrollmentToken}
                email={email}
                onComplete={(session) => {
                  if (session) applySession(session.accessToken, session.user);
                  else backToCredentials("MFA is enabled. Sign in again to continue.");
                }}
                onCancel={() => backToCredentials()}
              />
            </>
          ) : null}

          <p className="mt-8 text-xs text-ink-subtle">Secure access to your IT workspace</p>
        </div>
      </section>
    </div>
  );
}
