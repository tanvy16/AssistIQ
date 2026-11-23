# AssistIQ — Final submission report

**Date:** 19 Nov 2026 · **Scope:** completion, stabilisation, performance, security (MFA) and verification sprint on the existing codebase. No redesign; no data deleted or reseeded; Ollama not restarted; `.env` files not modified.

Status key — **PASS**: verified by a test or live run that actually executed successfully · **PARTIAL**: implemented but incomplete or only partly verified · **FAIL**: does not meet the requirement · **NOT IMPLEMENTED**.

Companion documents: `docs/DEMO_SCRIPT.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/SECURITY.md`. Earlier evidence (`docs/PPT_COMPLIANCE_AUDIT.md`, `docs/PRE_SUBMISSION_CHECK.md`, `docs/SUBMISSION_STATUS.md`) is preserved unchanged.

---

## 1. Executive summary

| | |
|---|---|
| **Already working before this sprint** | Ticketing with SLA due dates, role dashboards, grounded RAG chat with citations, chat → ticket escalation with reuse, policy-controlled *simulated* IT automation and password reset, admin observability, JWT + rotating refresh cookie, backend RBAC. Live A–E had passed on 23 Oct. |
| **Changed** | TOTP MFA (enrollment, QR, recovery codes, admin reset, strict/grace enforcement), login lockout, refresh-token families with reuse detection, password change, session management, `authz.denied` auditing, 422 no longer echoes passwords; access-token auto-renewal in the UI; fixed blank/zero dashboards; ticket-action error handling; honest toasts; new **Ticket Analytics** page (real SQL, snapshot-labelled); 2–5× faster API reads; isolated Docker test database with a guard that makes accidental Neon writes impossible. |
| **Verified now** | Frontend: 54/54 tests, typecheck, production build. Backend: **219/219** tests on the isolated DB (§7). Live on Neon: A–E all PASS (30 checks). MFA enrollment → sign-in → wrong code → recovery code exercised in the real browser UI (isolated stack). |
| **Still incomplete** | PPT items never built: OTP-gated *automation*, Vision AI, Docker Compose, PDF/DOCX ingestion, multi-agent split, adaptive routing, MTTR/FCR. Shared demo accounts are not MFA-enrolled (grace mode). Observability page still ~9 s on Neon. See `KNOWN_LIMITATIONS.md`. |
| **Safe to submit?** | **Yes, with the disclosures in KNOWN_LIMITATIONS.md.** Builds and tests pass, core workflows are live-verified, nothing simulated is presented as real. |

---

## 2. Architecture

```
React 18 + Vite + Tailwind (SPA, lazy-loaded pages, Recharts)
   │  REST + SSE · Bearer access token (memory) · HttpOnly refresh cookie (/api/v1/auth)
   ▼
FastAPI (127.0.0.1:18765)
   ├─ auth: bcrypt · JWT · rotating refresh families · TOTP MFA · lockout · rate limits
   ├─ RBAC deps (get_current_user / require_roles) · 403 → authz.denied audit
   ├─ services: tickets+SLA · dashboard · ticket analytics · knowledge · chat · IT requests · password reset · observability · audits
   ├─ LangGraph: chat graph (intent → retrieve → generate/escalate/create ticket/IT request/password reset)
   ├─ adapters: Chroma (hash-v1 384-d embeddings) · LLM (Ollama OpenAI-compatible) · MockIAM · MockExecution
   ▼
Neon PostgreSQL (us-east-2, ~260 ms RTT)        ChromaDB (local, chunk vectors)        Ollama llama3.2 (local)
```

## 3. Technology stack

Frontend: React 18.3, TypeScript 5.6, Vite 5.4, Tailwind 3.4, React Router 6, Recharts 3, Vitest 2. Backend: Python 3.14 venv, FastAPI 0.141, SQLAlchemy 2 (asyncpg), Alembic, Pydantic Settings, PyJWT, bcrypt 5, **cryptography 50 (new)**, **segno 1.6 (new)**, LangGraph 1.2, ChromaDB 1.5, httpx. Data: Neon PostgreSQL (migrations 0001–**0010**), Chroma. AI: Ollama `llama3.2:latest` locally.

## 4. Implemented features and status

| Area | Feature | Status | Evidence |
|---|---|---|---|
| Auth | Login / logout / refresh rotation | **PASS** | Live A; isolated `test_auth.py`, `test_security_mfa.py` |
| Auth | Access-token auto-renewal in UI (was: broken after 15 min) | **PASS** | Vitest `authFetch.test.ts` (single shared refresh, failure ends session) |
| Auth | TOTP MFA enrollment / login / recovery codes / disable / admin reset | **PASS** (isolated + browser) | 33 security tests; browser walkthrough §9 |
| Auth | Admin/agent MFA enforcement | **PARTIAL** | `strict` mode PASS in isolated tests; demo runs in `grace` (banner, not lockout). Demo accounts not enrolled. |
| Auth | Lockout, generic errors, password policy & change, session list/revoke | **PASS** (isolated) | `test_security_mfa.py` |
| RBAC | Backend role checks, IDOR protection, role-injection rejection | **PASS** | Live A (403s on Neon); isolated RBAC/IDOR tests |
| RBAC | Agents could post into other users' chats | **Fixed → PASS** | `test_ticket_and_conversation_idor` |
| Tickets | Create / list / detail / status transitions / SLA due badges | **PASS** | Live D/E; isolated `test_tickets.py` |
| Tickets | Agent resolving an unassigned ticket got 403 although the change committed | **Fixed → PASS** | `test_ticket_regressions.py` (auto-claim + 200) |
| Tickets | SLA auto-escalation on breach | NOT IMPLEMENTED | — |
| Chat | Grounded answer with real citations, streaming | **PASS** | Live C (KB-1 → "E2E VPN Connect Guide", similarity 0.854) |
| Chat | Human escalation → persisted ticket, reuse on repeat | **PASS** | Live D (`TICK-00172` reused) |
| Knowledge | Text KB, publish → chunk → hash embedding → Chroma | **PARTIAL** | Existing tests; no PDF/DOCX |
| Automation | Policy allow / deny / escalate, simulated execution labelled | **PASS** (isolated) | `test_it_policy.py`, `test_it_requests.py`; live test F not authorised |
| Dashboards | Real SQL counts; error → "Could not load" (was: fabricated zeros) | **PASS** | Live B; browser |
| Analytics | Ticket Analytics (status, priority, category, created vs resolved, SLA, escalations, 7/14/30/90 d) | **PASS** | `test_ticket_analytics_is_admin_only_and_real`; browser |
| Observability | AI telemetry charts, honest empty states, mock labels | **PARTIAL** | Works; ~9 s on Neon; whole page fails if one endpoint fails |
| Audit | Security events + `authz.denied`, event-type filter, recursive redaction | **PASS** | Live A (6 `authz.denied` rows returned); isolated |

## 5. Actual AI / RAG workflow

1. `POST /chat/conversations/{id}/messages/stream` → `ChatService.send_message_stream`.
2. LangGraph `detect_intent` (keyword map + optional lightweight scorer) → route.
3. `knowledge_query` → `retrieve_context`: hash-v1 embedding → Chroma top-k over **published** chunks → join to SQL metadata.
4. Prompt places retrieved chunks in a DATA section with instructions that data cannot change instructions or trigger tools.
5. Ollama streams tokens (SSE `token` events) → persisted user + assistant messages, `MessageCitation` rows built only from retrieved chunks, telemetry, `chat.message.sent` audit.
6. Confidence: `HIGH_CONFIDENCE` / limited / `NO_EVIDENCE` (no evidence → explicit note, never invented sources).
7. Escalation (`/escalate` or intent) → `ensure_ticket_for_conversation` → real `TICK-#####` returned only after persistence.

Measured live (test C): intent `knowledge_query`, confidence `HIGH_CONFIDENCE`, 74 token events, **TTFT 59.7 s, total 82.1 s** (cold model; prewarm deliberately disabled). This is model inference on a laptop CPU and is reported separately from page performance.

## 6. Database and API design

- 10 Alembic migrations. **0010_security_mfa** (applied to Neon on 19 Nov with explicit approval; tested upgrade → downgrade → upgrade on the isolated DB) is additive only: `user_mfa`, `mfa_recovery_codes`, `auth_login_throttle`, and `refresh_tokens.family_id / replaced_by_id / mfa_verified`.
- New endpoints: `POST /auth/mfa/verify`, `GET /auth/mfa/status`, `POST /auth/mfa/enroll/start|verify`, `POST /auth/mfa/recovery-codes/regenerate`, `POST /auth/mfa/disable`, `POST /auth/password/change`, `GET /auth/sessions`, `POST /auth/sessions/revoke-others`, `POST /users/{id}/mfa/reset` (admin), `GET /analytics/tickets?days=7|14|30|90` (admin), `GET /audits?event_type=` filter.
- Login response is now one of: signed in / `mfa_required` + challenge token / strict-mode enrollment token.

## 7. Test results (exact commands)

| Command | Result |
|---|---|
| `cd frontend; npx vitest run` | **13 files, 54 tests passed**, exit 0 (was 36 at the 23 Oct audit, 45 at sprint start) |
| `cd frontend; npx tsc -b` | exit 0 |
| `cd frontend; npm run build` | exit 0, 733 modules, built in 20.5 s |
| Backend baseline, isolated DB, **before any feature change** | **185 passed**, 0 failed, 426 s |
| Backend guard check: full `pytest` with a fake *non-loopback* `DATABASE_URL` | 83 passed, **102 skipped** (every DB-backed test), 0 errors — proves Neon cannot be written by an accidental run |
| `tests/test_security_mfa.py` (isolated) | **33 passed** |
| `tests/test_ticket_regressions.py` + `tests/test_tickets.py` (isolated) | 15 passed |
| `tests/test_observability.py` (isolated) | 10 passed (61 s) |
| Full backend suite, isolated DB, first final run | 210 passed, **9 failed** — all in `test_prewarm.py`, a regression from the new `LLM_PREWARM_ENABLED` check (tests use settings stubs without the field). Fixed with a tolerant `getattr`. |
| Guard check after the fix (fake non-loopback URL) | 96 passed, 123 skipped, 0 failed |
| **Full backend suite, isolated DB, final rerun** (same environment as `scripts/run_isolated_tests.ps1`) | **219 passed, 0 failed**, exit 0, 914 s |

Not run: any pytest against Neon (forbidden), live test F (IT automation), forced persistence-failure test 8, linting (no linter/formatter is configured in the repository — none of `eslint`, `prettier`, `ruff`, `flake8` is present).

## 8. Performance (measured before and after, same Neon, same harness)

Method: `perf_api.py` (scratchpad) — one login per role, 1 warm-up, then 15 sequential timed GETs per endpoint; Observability = its 12 parallel requests as one batch. Network round trip to Neon measured at **222–325 ms (median 259 ms)** by TCP connect.

Root cause found: every request paid ~4 fixed round trips (pool pre-ping, BEGIN, query, ROLLBACK) plus one per SQL statement; `/ready` (`SELECT 1`) alone took 1.64 s. Statement counts per endpoint were measured in-process: dashboard 5/7/10 (employee/agent/admin), observability 112 across 12 endpoints.

Changes: removed `pool_pre_ping` (→ `pool_recycle=240 s`, under Neon's idle suspend); GET/HEAD requests use AUTOCOMMIT sessions (no BEGIN/ROLLBACK; READ COMMITTED semantics unchanged; verified no GET handler writes); independent dashboard and observability aggregates run concurrently on pooled sessions; pool 10 + 10 overflow so the observability fan-out reuses warm connections.

| Endpoint (p50 / p95 ms) | Before | After | Change |
|---|---|---|---|
| `GET /health` (no DB) | 8.6 / 9.7 | 6.9 / 8.2 | — |
| `GET /auth/me` | 1137 / 1163 | **236 / 238** | 4.8× |
| Dashboard — employee | 2668 / 2946 | **932 / 1599** | 2.9× |
| Dashboard — agent | 2818 / 3279 | **926 / 1363** | 3.0× |
| Dashboard — admin | 3465 / 3828 | **1433 / 1882** | 2.4× |
| Tickets — employee | 1820 / 1831 | **910 / 915** | 2.0× |
| Ticket queue — agent | 2096 / 2293 | **1137 / 1400** | 1.8× |
| Knowledge list | 1629 / 1845 | **614 / 1022** | 2.7× |
| Conversations list | 1681 / 2763 | **464 / 1640** | 3.6× |
| Users (admin) | 1648 / 1749 | **481 / 695** | 3.4× |
| Audit log (admin) | 1831 / 2079 | **699 / 1144** | 2.6× |
| Observability page (12 parallel) | 17 001 / 18 331 | **9 366 / 9 576** | 1.8× |
| Login (single sample) | 3394–5213 | 2877–4608 | small (now does more security work) |

Frontend: the polling hook's in-flight flag survived React StrictMode's mount → unmount → mount, so in `npm run dev` every dashboard, ticket list and observability page initially rendered **empty/zero for up to 20–45 s** until the next poll. Fixed (per-request controller); data now appears on the first response. Shared deduplicated requests no longer get aborted by another component's unmount. Bundle: entry 61.1 → 64.4 kB gzip (+MFA login step); total 238 → 253 kB gzip; Recharts stays in a lazy chunk used only by the two chart pages.

AI latency is reported separately in §5 and is **not** improved by these changes.

## 9. Live verification (shared Neon, authorised scope A–E only)

API on `127.0.0.1:18765` (new code, migration 0010, startup prewarm disabled so the only generation was test C). Script stops on the first unexpected result; no passwords or tokens were printed. **All 30 checks PASS.**

| Test | Account | Expected writes | Actual |
|---|---|---|---|
| **A** Auth/RBAC | employee, agent, admin | refresh token + `auth.login` per login; `authz.denied` per 403 | 3 logins 200 (agent/admin `mfa_enrollment_required: true` — grace); `/auth/me` roles match; employee 403 on `/audits`, `/users`, `/observability/cost`, `/analytics/tickets`; agent 403 on `/audits`, `/users`; admin 200; 6 `authz.denied` rows visible to admin |
| **B** Dashboard | all | none | 200 for all; employee 5 tickets (4 open, 1 in progress), agent/admin 7; SLA compliance `null` → "—"; admin-only sections present only for admin |
| **C** Grounded chat | employee | conversation, 2 messages, citation, telemetry, audit; 1 generation | conversation `1a77a036-…`; streamed answer (HQ gateway, company VPN client, `[KB-1]`); 1 persisted citation to doc `2f378f02` chunk `4a4f79d7`; no `TICK-` in answer |
| **D** Escalation | employee | ticket + event + escalation; repeat reuses ticket | `TICK-00172` (`0722cdbb-…`) created, status open; repeat → same ticket, new escalation; conversation `escalated` |
| **E** Agent update | agent | status update + `ticket.status_changed` | in queue; employee PATCH 403; agent `open → in_progress` 200; events `ticket.created`, `ticket.status_changed open→in_progress` |

**Code changed after the live run** (covered by isolated tests and the browser check, *not* re-run live on Neon to stay within the single authorised A–E pass): agent auto-claim when changing an unassigned ticket's status (`test_ticket_regressions.py`); `LLM_PREWARM_ENABLED` tolerant settings access (`test_prewarm.py`); dashboard loading-state and donut-colour fixes (browser, isolated stack). In test E the ticket was moved `open → in_progress` while unassigned; with the auto-claim change the same action now also assigns it to the agent.

Other Neon activity this sprint (all within scope A, read-only otherwise): 6 additional logins for the before/after latency measurements, and the approved migration. No rows were deleted.

**Browser verification (isolated stack — synthetic users on the Docker DB, because reading the real demo passwords into the assistant was blocked by policy):** admin dashboard loads data on first render; amber MFA banner (grace); Security → set up authenticator → password → server-rendered QR + setup key → code → MFA enabled, 10 recovery codes shown once, other sessions revoked, session shown "MFA verified"; sign out → sign in now requires step 2; wrong code rejected with message; recovery code accepted; Ticket Analytics charts match seeded rows exactly; Observability honest empty states; Users page MFA column and coverage; employee dashboard and IT Requests (simulated wording). The agent UI was not walked through in the browser this round (agent flow covered by live test E and isolated tests).

## 10. Security and RBAC

See `docs/SECURITY.md` (architecture diagram, MFA controls table, token lifecycle, RBAC matrix, audit event catalogue, key configuration, recovery procedures). Security acceptance criteria:

| # | Criterion | Status |
|---|---|---|
| 1 | MFA enrollment and verification work | **PASS** (isolated tests + browser) |
| 2 | Enrolled users cannot bypass MFA | **PASS** (isolated) |
| 3 | Admin and agent MFA enforcement | **PARTIAL** — strict mode PASS (isolated); deployed demo uses grace |
| 4 | Recovery codes secure and single-use | **PASS** |
| 5 | Token rotation and revocation | **PASS** |
| 6 | Rate limiting and account protection | **PASS** (single-process limiter) |
| 7 | Backend RBAC enforced | **PASS** (live + isolated) |
| 8 | No sensitive leakage | **PASS** for logs, audit payloads and 422 bodies tested |
| 9 | Security tests pass in isolation | **PASS** (33/33) |
| 10 | Documentation accurate | **PASS** |

Not implemented: email/SMS OTP, password reset by email (no email delivery — nothing claims a message was sent), WebAuthn, SSO, CAPTCHA, distributed rate limiting, tamper-proof audit storage.

## 11. Dashboard and telemetry

| Chart | Data source | Interactions |
|---|---|---|
| Ticket status mix (all dashboards) | `/dashboard/summary` SQL counts | legend, live polling 20 s |
| **Created vs resolved per day** | `/analytics/tickets` `daily[]` (SQL `date_trunc` by UTC day, zero-filled) | date range 7/14/30/90, tooltip, legend, empty state when the window has no activity |
| **Status / SLA donuts, priority / category bars** | `/analytics/tickets` | tooltips, semantic colours (open teal, resolved green, at risk amber, breached coral) |
| **Escalations per day** | `escalations` + chat-created tickets | same |
| AI request volume, outcomes, latency, model usage, tokens, cost, RAG, intents, IT/password-reset workflow charts | `/observability/*` telemetry tables | 24h/7d/30d/custom, tooltips, empty states, "Not recorded" for unknown tokens/cost |

Live vs snapshot: dashboards and observability show **LIVE** only after a successful poll while the tab is visible (Stale on error / hidden). Ticket Analytics is labelled **SNAPSHOT · not auto-refreshing** with a manual Refresh button. No chart uses hardcoded or generated data (frontend audit found no literal metric arrays or `Math.random`).

## 12. UI finalisation

Kept the dark charcoal / forest-green system. Added: Security page, MFA login step, enrollment flow, recovery-code panel, Users MFA column, Ticket Analytics page, `DataUnavailable` error state. Fixed: violet no longer used for "Open"/"On track" in analytics donuts (semantic tokens, legend matches ring); duplicate "Analytics → Observability" nav entry replaced by a real page; no empty-state copy ("no tickets") is shown while data is still loading; ticket action buttons disable while pending and show errors; toasts reflect real returned status.

## 13. PPT compliance (update to `PPT_COMPLIANCE_AUDIT.md`)

| PPT claim | 23 Oct | Now |
|---|---|---|
| JWT + RBAC + **OTP** (slide 6) | RBAC partial, OTP not implemented | RBAC **PASS** live; TOTP for **sign-in** PASS (isolated + browser) |
| OTP-gated **automation** (slides 4, 8) | NOT IMPLEMENTED | **NOT IMPLEMENTED** (automation still gated by policy + session email) |
| Measure MTTR / deflection | NOT IMPLEMENTED | NOT IMPLEMENTED (analytics show created/resolved/SLA/escalations only) |
| SLA compliance analytics | PARTIAL | **PASS** for "SLA met on resolution" % and active SLA status (no auto-escalation) |
| Autonomous resolution without humans | FAIL | FAIL — simulated and human-in-the-loop by design |
| Vision AI, Docker Compose, PDF/DOCX, 4 agents, adaptive routing, public GitHub | NOT IMPLEMENTED / FAIL | unchanged |

## 14. Mocked vs real

| Real | Simulated |
|---|---|
| Tickets, SLAs, comments, events, escalations, chat history, citations, telemetry, audit log, users, MFA, password change, sessions, analytics | Password-reset *execution* (MockIAM), software/access *execution* (MockExecution) — both return `simulated: true` and the UI says so |

## 15. Startup instructions

```powershell
# backend (first time after this sprint)
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # adds cryptography, segno
alembic upgrade head                      # Neon is already at 0010_security_mfa
python -m uvicorn app.main:app --host 127.0.0.1 --port 18765
```

```powershell
# frontend
cd frontend
npm install
npm run dev                               # http://127.0.0.1:5173
```

Ollama must already be serving `llama3.2:latest` on 11434. If port 5173 is taken by another project, see README → Ports (add the new origin to `CORS_ORIGINS`). Tests: README → Testing (`backend/scripts/run_isolated_tests.ps1`).

## 16. Screenshots

Captured during browser verification in the assistant's preview pane (not saved to the repository): login, admin dashboard with MFA banner, Security page (not enabled → QR → recovery codes → enabled), MFA sign-in step with error, Ticket Analytics (charts and donuts), AI Observability empty states, Users MFA column, employee dashboard, IT Requests. To include images in the written report, capture them during the demo rehearsal.

## 17. Files changed (no git history exists; a pre-sprint snapshot was kept outside the repo)

Backend: `app/core/{config,deps,security,database,rate_limit,mfa*}.py`, `app/main.py`, `app/models/{enums,refresh_token,security*,__init__}.py`, `app/schemas/auth.py`, `app/api/router.py`, `app/api/v1/{auth,users,audits,analytics*}.py`, `app/services/{auth_service,mfa_service*,ticket_analytics_service*,dashboard_service,observability_service,chat_service,ticket_service}.py`, `alembic/versions/0010_security_mfa.py*`, `requirements.txt`, `scripts/run_isolated_tests.ps1*`, `tests/conftest.py`, `tests/test_security_mfa.py*`, `tests/test_ticket_regressions.py*`.
Frontend: `lib/{api,ai,users,usePolledQuery,queryMemory,security*,analytics*,navigation}.ts`, `lib/{authFetch*,navigation}.test.ts`, `context/AuthContext.tsx`, `App.tsx`, `pages/{LoginPage,SecurityPage*}.tsx`, `pages/admin/{AdminDashboard,AdminUsersPage,AdminTicketAnalyticsPage*}.tsx`, `pages/agent/AgentDashboard.tsx`, `pages/employee/EmployeeDashboard.tsx`, `components/{layout/AppShell,tickets/TicketDetailView,passwordReset/PasswordResetDetailView,it/ITRequestDetailPage}.tsx`, `components/charts/{DonutChart,DailyMultiSeriesChart*}.tsx`, `components/security/*`, `components/ui/DataUnavailable.tsx*`; all `lib/*.ts` API wrappers now use `authFetch`.
Docs: this report*, `DEMO_SCRIPT.md`*, `KNOWN_LIMITATIONS.md`*, `SECURITY.md`, `README.md`. (`*` = new file.) Tooling: `.claude/launch.json`*.
