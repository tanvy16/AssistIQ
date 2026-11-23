# AssistIQ — Known limitations

**Date:** 19 Nov 2026 (final submission sprint)
Companion to `docs/FINAL_SUBMISSION_REPORT.md`. Everything here is a deliberate disclosure: say it in the viva rather than letting an examiner discover it.

## 1. Simulated (mock) functionality — never presented as real

| Area | What really happens | What does **not** happen |
|---|---|---|
| Password reset workflow (`/password-resets`) | Session email verification → risk/policy check → `MockIAMAdapter` returns `simulated: true` | No real password, Active Directory, Okta or IdP change. `User.password_hash` is never written by this workflow. |
| Software install / access requests (`/it-requests`) | Policy engine allow / deny / escalate → allow-listed runbook → `MockExecutionAdapter` (`simulated: true`) | No software is installed, no shell / PowerShell / package manager is invoked, no access is granted anywhere. |
| UI | IT Requests page: "Actions are simulated and never change this machine." Success toasts now state "nothing was installed or changed" and reflect the **returned status** (failed / rolled back shows as an error). | — |

The **account Security page** (MFA, password change, sessions) is *real*: it changes the user's AssistIQ login password and MFA state. Do not confuse it with the simulated "Password Reset" IT workflow.

## 2. Not implemented (PPT Review-1 promises)

| PPT promise | Status |
|---|---|
| OTP-gated **automation** (slides 4, 6, 8) | **NOT IMPLEMENTED** for automation. TOTP MFA now protects **sign-in** (see `docs/SECURITY.md`); IT/password-reset automation is still gated by policy + session email verification, not OTP. |
| Vision AI / screenshot / OCR troubleshooting | NOT IMPLEMENTED |
| Docker Compose deployment | NOT IMPLEMENTED (Docker is used only for the disposable isolated **test** database) |
| PDF / DOCX knowledge ingestion | NOT IMPLEMENTED — knowledge is title + body text |
| Four independent agents (Intent / RAG / Vision / Automation) | NOT IMPLEMENTED as separate agents — one LangGraph workflow with specialised nodes |
| Adaptive model routing (complexity / latency / cost / privacy) | NOT IMPLEMENTED — pluggable adapters, fixed selection |
| MTTR, FCR, deflection metrics | NOT IMPLEMENTED — do not quote them. Ticket Analytics reports created/resolved/SLA/escalations only. |
| Automatic SLA-breach escalation | NOT IMPLEMENTED — breaches are counted and shown, not auto-escalated |
| Real IAM / AD / email delivery | NOT IMPLEMENTED — no email is ever sent; nothing claims it was |
| Public GitHub repository with history | NOT DONE — local repository has no commits |

## 3. Security limitations (details in `docs/SECURITY.md`)

- **MFA enforcement mode.** Admin/agent MFA is *required* by policy, but outside production the default mode is `grace`: privileged users without MFA can still sign in and see a persistent "set up MFA" banner. `strict` mode (no access token until enrolled) is implemented and tested in isolation, and is the default when `APP_ENV=production`. The shared demo accounts were **not** enrolled during this sprint (that would have been an unapproved write and would change how the demo logs in).
- **MFA encryption key.** `MFA_ENCRYPTION_KEY` is not set in the local `.env` (env files were not modified). In development the Fernet key is derived from `JWT_SECRET_KEY` via HKDF and a warning is logged; rotating `JWT_SECRET_KEY` would make stored TOTP secrets undecryptable (users would need recovery codes or an admin MFA reset). Production refuses to start without a dedicated key.
- **Lockout keyed by email** (5 failures / 15 min → 15 min lock). This blocks password guessing but can be abused to temporarily lock a known account (denial of service). No CAPTCHA.
- **In-memory rate limiting**, single API process only; not shared across instances.
- **Access token in memory, refresh token in an HttpOnly cookie** (`SameSite=Lax`, `Secure` required in production). There is no separate CSRF token: the only cookie-authenticated endpoints are `/auth/refresh` and `/auth/logout`, protected by SameSite and strict CORS. All data endpoints require a Bearer header.
- **Audit log is an ordinary table** — append-only by API, not tamper-proof (anyone with DB credentials can modify rows).
- **Recovery for a fully locked-out user** (lost device *and* recovery codes) is an admin reset with admin password re-entry; identity verification before the reset is a manual, out-of-band process.
- **Prompt injection.** Retrieved knowledge is labelled as untrusted DATA in the prompt and cannot trigger tools, but the LLM can still echo injected text. In live test C the model did not follow an embedded "IAM password reset" instruction but did mention the topic.
- No WebAuthn/passkeys, no SSO, no email/SMS OTP, no breached-password check.

## 4. Performance limitations

- The database (Neon, us-east-2) is **~260 ms per network round trip** from the demo machine. Every SQL statement costs at least one round trip, so page loads are dominated by network latency, not computation. After this sprint's optimisations typical reads are 0.2–1.4 s (see report §8).
- **AI Observability** issues 12 parallel requests (~112 SQL statements) and still takes ~9 s to load on Neon (was ~17 s). One failing endpoint blanks the whole page (`Promise.all`); per-section error handling was not attempted this close to submission.
- **Local LLM latency.** `llama3.2` via Ollama on this laptop: time-to-first-token **59.7 s** and total **82.1 s** when the model was cold (startup prewarm deliberately disabled for the live test to avoid an extra generation). With the normal startup prewarm the model is kept loaded, which reduces the cold-load portion; a warm TTFT was **not** measured this sprint.
- Sign-in costs 2.9–4.6 s (bcrypt + ~8 sequential round trips for lockout, user lookup, MFA state, token and audit writes).

## 5. Environment / operational

- Port **5173** is currently used by another local project's Vite server; AssistIQ's dev server then falls back to another port, which must be in `CORS_ORIGINS` (see README "Ports").
- Full backend `pytest` must run against the disposable Docker database (`backend/scripts/run_isolated_tests.ps1`). The test fixtures delete whole tables; `tests/conftest.py` now refuses to run DB-backed tests against any non-loopback database.
- Telemetry token counts depend on the provider; Ollama may not report them, and the UI then shows "Not recorded" instead of a number.
- No unique DB constraint on `tickets.conversation_id`; chat→ticket reuse is application-level (two simultaneous escalations could still create two tickets).
