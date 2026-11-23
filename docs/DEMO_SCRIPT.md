# AssistIQ — 6-minute demonstration script

Uses the existing seeded **employee**, **agent** and **admin** accounts (credentials are in `backend/.env` as `SEED_*`; never show that file on screen). Everything below was exercised during the final sprint; timings are what to expect on this laptop with Neon (~260 ms per database round trip) and local Ollama.

## Before the examiner arrives (5 min)

1. Start the API (keep the normal startup prewarm so the model is loaded):
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn app.main:app --host 127.0.0.1 --port 18765
   ```
   Wait for `Local LLM keep-alive prewarm completed` in the log. `GET http://127.0.0.1:18765/api/v1/ready` → `{"status":"ready","database":"connected"}`.
2. Start the frontend: `cd frontend; npm run dev`. If Vite says port 5173 is in use and picks another port, either stop the other project's server or add that origin to `CORS_ORIGINS` before starting the API (README → Ports).
3. Open three browser profiles / windows (employee, agent, admin) and sign each in once, so login latency (~3–5 s) is not spent on stage.
4. **Optional MFA demo account:** MFA is best shown on the *employee* account (optional for that role), so admin/agent sign-ins stay unchanged. Have Google/Microsoft Authenticator on your phone. Afterwards disable it in Security (password + code), or keep it — then that account needs the phone for every sign-in.

## 0:00 – 0:30 Framing (say this)

> "AssistIQ is an IT helpdesk with ticketing and SLAs, a knowledge-grounded AI assistant that cites its sources, human escalation into real tickets, policy-controlled IT automation that is **simulated**, and admin observability. React + FastAPI + PostgreSQL (Neon) + Chroma + a local Llama 3.2 model through Ollama, orchestrated with LangGraph."

## 0:30 – 2:30 Employee

1. **Dashboard** — real counts from SQL; the "Live" badge means it polls every 20 s. If the API were down it would say "Could not load…", never show zeros.
2. **AI Chat** → *New conversation* → ask:
   *"How do I connect to the corporate VPN using the company VPN client, and which gateway should I choose?"*
   - Tokens stream in. Say honestly: *"The model runs locally on this laptop, so the first token takes a while — tens of seconds when cold."*
   - Point at the **[KB-1] citation** → "E2E VPN Connect Guide". Citations are built only from retrieved published chunks; with no evidence it says so instead of inventing sources.
3. Click **Request human** → toast shows a real `TICK-#####` only after the ticket was saved. Click it again → same ticket number (reused, not duplicated).
4. **IT Requests** → point at "Actions are simulated and never change this machine." (Do not claim anything was installed.)
5. **Security** → show MFA status, *Set up authenticator* → password → scan QR with the phone → enter code → 10 one-time recovery codes ("shown once, stored only as hashes"). *(Optional, ~60 s.)*

## 2:30 – 3:45 Agent

1. **Ticket Queue** → the new `TICK-#####` is there, unassigned, with its SLA due badge.
2. Open it → **Mark In Progress** → status and timeline update (`ticket.status_changed` event). Mention: an agent who works an unassigned ticket automatically claims it.
3. Show that the agent dashboard banner asks the agent to set up MFA: "MFA is required for agents and admins; in this development build enforcement is in grace mode so the demo accounts are not locked out — production uses strict mode."

## 3:45 – 5:30 Admin

1. **Ticket Analytics** — created vs resolved per day, status / priority / category distributions, SLA status, chat escalations. Switch 7 / 30 / 90 days; hover for tooltips. "This is a **snapshot** with a Refresh button, not a live stream — and days without tickets are real zeros; empty windows show an empty state instead of a fake trend."
2. **AI Observability** — request volume, outcomes, latency, model usage, tokens ("Not recorded" when Ollama doesn't report them), and the explicit *mock IAM / mock execution* labels. Takes a few seconds to load — it aggregates a lot over a remote database.
3. **Users** — MFA column and "MFA coverage x of y"; *Reset MFA* is the recovery path for a user who lost device and codes (requires the admin's own password, signs out all their sessions).
4. **Audit Log** — find `auth.login`, `mfa.enabled` (if you did step 5 above), `authz.denied` rows produced when an employee tries an admin URL.
5. Optional RBAC proof: in the employee window, visit `/app/admin/audits` → redirected home; the API itself returns 403 and that denial appears in the Audit Log.

## 5:30 – 6:00 Close with honesty (say this)

> "Password resets and software installs are simulated through mock adapters; no real identity or machine is changed. Vision AI, Docker deployment, PDF ingestion, adaptive model routing and MTTR/FCR metrics from the Review-1 slides are not implemented — they are listed in KNOWN_LIMITATIONS. What *is* real: tickets, SLAs, grounded citations, escalation into persisted tickets, TOTP MFA with recovery codes, rotating refresh tokens with reuse detection, lockout, backend RBAC and audit logging, all covered by an isolated test suite."

## If something goes wrong

| Symptom | Say / do |
|---|---|
| Chat is slow or times out | "Local CPU inference; the answer is persisted when it completes." Fall back to an existing cited conversation in the history list. |
| "Could not load …" panel | It is the honest error state; check the API window, click Retry. |
| Signed out unexpectedly | Sessions refresh automatically; if the refresh token expired or was revoked (e.g. after MFA enrollment on another window), sign in again. |
| "Too many failed sign-in attempts" | Lockout is working (5 failures → 15 min). Use another account; do not reset data. |
