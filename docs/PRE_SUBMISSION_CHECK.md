# AssistIQ pre-submission verification

**When:** 23 Oct 2026, evening  
**Rule:** no new features, no schema/UI/dependency changes, **no application code edits**, no Ollama restart. Isolated checks first; live A–E against shared Neon **only after explicit approval**. Test F not run.

Application code was **not** modified for this check. This file is the verification record.

---

## Running process

### Previous process (stopped with approval)

| Item | Observation |
|---|---|
| Port `18765` | Was **Listen** `127.0.0.1` |
| PID | **32520** (`python`, start **23 Oct 2026 15:09:07**) |
| Identity | AssistIQ uvicorn: `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18765` |
| Parent | PID **10972**, same command line (venv launcher); both exited when 32520 was stopped |
| Not touched | Spotify PID 28872 (stale parent-PID reuse under 10972); Ollama; other listeners |

**Identity check before stop:** `Get-NetTCPConnection -LocalPort 18765` OwningProcess **32520**; command line was this project's uvicorn. Then `Stop-Process -Id 32520`. After stop: 32520 gone, 10972 gone, **18765 free**.

### Current process (started after stop)

| Item | Observation |
|---|---|
| Port `18765` | **Listen** `127.0.0.1` |
| Shell PID | **12580** (PowerShell that launched uvicorn) |
| Worker PID | **16248** (`Started server process [16248]`) |
| Command | `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18765` from `backend` |
| Startup | Application startup complete **19:20:51**; registry ensure completed (SELECT existing keys, COMMIT; no extra model rows logged) |
| Prewarm | Inherent to lifespan. `POST http://127.0.0.1:11434/api/generate` **HTTP 200**; log `Local LLM keep-alive prewarm completed` at **19:21:26**. **Ollama was not restarted.** |

**Health (live, read-only, performed):**

```text
GET http://127.0.0.1:18765/health      → 200 {"status":"ok"}
GET http://127.0.0.1:18765/api/v1/ready → 200 {"status":"ready","database":"connected"}
```

Ready used `SELECT 1` then ROLLBACK (no table writes). Application code was **not** modified.

**Later the same evening:** Vite started from `frontend` (`npm run dev`) because 5173 was free. Local: `http://127.0.0.1:5173/`. Backend worker remained **16248** (not restarted). Application code was **not** modified.

---

## Workflow results

| # | Workflow | Status | Tests vs live |
|---|---|---|---|
| 1 | Frontend production build + existing frontend tests | **PASS** | Isolated Vitest + production build. Vite also started for live UI. |
| 2 | Authentication and employee/agent/admin authorization | **PASS** (live A) | Seeded logins 200. Role `/me` matches. Admin-only routes 403 for employee/agent. Employee cannot GET another requester’s ticket (403). See Test A note on `scope=queue`. |
| 3 | Employee chat grounded answer + genuine citations | **PASS** (live C) | One published KB doc retrieved; one conversation; one Ollama-backed answer with citation to that doc id/title/chunk. |
| 4 | Request human → persist or reuse ticket; ID only after success | **PASS** (live D) | First escalate 201 `TICK-00171`; GET ticket 200; second escalate same ticket id/number, new escalation id. |
| 5 | Ticket in agent UI; supported status updates persist | **PASS** (live E) | Ticket in agent queue API + browser queue; PATCH open→`in_progress` persisted; employee PATCH 403. |
| 6 | Automation policy allow/deny/escalate; mock labeled simulated | **PASS** (policy/mock units) | Isolated units only. **Test F not run.** |
| 7 | Dashboard analytics real or explicitly unavailable | **PASS** (live B) | Employee/admin UI numbers matched `/dashboard/summary`. SLA `"—"`. Tokens were `"Not recorded"` before chat, then real counts after C. |
| 8 | Failure paths never report success that did not happen | **PARTIAL** | Isolated escalate-failure tests still stand. Live persist-failure not injected. Employee status PATCH correctly 403. |

**Live employee → cited answer → ticket → agent status loop: verified** (C→D→E on conversation `8e97b696-…` / `TICK-00171`). Test F was authorized-out and **not** executed.

---

## Commands and actual results

```text
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_prewarm.py tests/test_default_models.py tests/test_chat_ticket_persistence.py tests/test_it_policy.py tests/test_chunking_service.py tests/test_embedding_service.py tests/test_chroma_adapter.py tests/test_hardening.py::test_json_safe_coerces_validation_ctx_value_error tests/test_hardening.py::test_rag_prompt_treats_retrieved_text_as_data tests/test_hardening.py::test_production_requires_secure_cookie tests/test_hardening.py::test_production_rejects_wildcard_cors -q --tb=line
```

**Result: 56 passed**, 1 chromadb deprecation warning, **exit 0**.

```text
cd frontend
npm test
npm run build
```

**Result:** Vitest **9 files, 36 passed**. `tsc -b && vite build` **122 modules**, **built in 12.26s**, **exit 0**.

**Restart (approved, 23 Oct 2026 ~19:20):**

```text
Stop-Process -Id 32520
cd backend
$env:PYTHONUNBUFFERED = '1'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18765
```

**Result:** worker **16248** listening; `/health` 200; `/api/v1/ready` 200 `database: connected`; prewarm HTTP 200 (startup lifespan only).

**Frontend start (5173 was free):**

```text
cd frontend
npm run dev
```

**Result:** Vite `http://127.0.0.1:5173/` ready. No unrelated process was stopped.

**Not run:** full `pytest`, Neon-writing pytest modules (`test_tickets.py`, `test_chat.py` HTTP, `test_auth.py`, `test_it_requests.py`, …), Test F IT automation, Test G forced persist failure, extra Ollama generations after the single Test C chat.

---

## Evidence notes (inspection, not live)

- **AuthZ:** `get_current_user` + `require_roles` (`backend/app/core/deps.py`); `ProtectedRoute` + `App.tsx` role trees; admin-only audits/observability/KB write.
- **Citations:** built only from retrieved published chunks (`retrieve_context.py`). Chroma failure → empty citations (isolated test). Prompt treats retrieved text as DATA (`test_rag_prompt_treats_retrieved_text_as_data`).
- **Tickets from chat:** `ensure_ticket_for_conversation` reuses by `conversation_id` (no unique DB constraint). Escalate/create nodes and ChatPage require a real `ticket_number` before success copy.
- **Agent updates:** `PATCH /api/v1/tickets/{id}` uses `VALID_STATUS_TRANSITIONS`; closed has no outbound transitions.
- **Mock automation:** `evaluate_policy` allow/deny/escalate; `MockExecutionAdapter` `simulated: true`; UI `statusExplanation("completed")` states no real install.
- **Analytics:** ticket counts from SQL; token/cost formatters do not invent numbers.
- **Honesty:** escalate `TicketError` → “could not create”; no `TICK-` in that answer.

---

## Live A–E (23 Oct 2026, ~20:35–20:50 IST)

Preflight: PID **16248** still this project's uvicorn on `127.0.0.1:18765`. `GET /health` 200. `GET /api/v1/ready` 200 `database: connected`. 5173 was free → Vite started from `frontend`. Ollama was **not** restarted. Application code was **not** changed. Credentials were existing `SEED_*` accounts only; passwords and tokens are not recorded here.

### Test A — Auth and RBAC — **PASS**

**Plan:** `POST /api/v1/auth/login` for employee, agent, admin. Then `GET /api/v1/auth/me`, `GET /api/v1/dashboard/summary`, `GET /api/v1/tickets`, `GET /api/v1/tickets?scope=queue`. Employee `GET /api/v1/audits`, `/observability/cost`, `/users`. Employee `GET` a foreign queue ticket. Browser: employee login, dashboard, `/app/agent/queue` should not stay on the agent route.

**Expected writes:** `refresh_tokens` + login `audit_events` per login. GETs read-only. No new users.

**Observed:**

| Check | Result |
|---|---|
| Employee / agent / admin login | **200**, access token issued, refresh cookie set |
| `GET /auth/me` | **200**; roles `employee` / `agent` / `admin`; ids `cffbe92a-…` / `10b9371a-…` / `90005ec7-…` |
| Dashboards | **200** for all three roles |
| Employee `GET /tickets?scope=queue` | **200**, 4 rows, **all requester = employee**. Does **not** 403. Does **not** leak `TICK-00161` / `TICK-00151` |
| Agent queue | **200**, 6 unassigned tickets including other requesters |
| Employee `GET /tickets/c77cd140-…` (`TICK-00161`, other requester) | **403** |
| Employee `/audits`, `/observability/cost`, `/users` | **403** `Insufficient permissions` |
| Agent `/audits` | **403** |
| Admin `/audits` | **200** (total 2219 at that moment) |
| Admin `/users` | **200**, **total 46** (no user created) |
| Browser | Employee dashboard at `/app/employee`. Navigate `/app/agent/queue` → redirected to `/app/employee` |

**Expected vs writes:** matches. Extra browser employee login later added another refresh/audit pair.

### Test B — Dashboard — **PASS**

**Plan:** `GET /api/v1/dashboard/summary`; compare employee and admin UI. No sample rows inserted.

**Expected writes:** none beyond auth.

**Observed (API then UI):**

| Surface | API | UI |
|---|---|---|
| Employee `/app/employee` | tickets total 4, open 4, in_progress 0, resolved 0; `sla_compliance_pct` null; knowledge/users/ai **null** (non-admin) | My tickets **4**, Open **4**, In progress **0**, Resolved **0**. Same four ticket numbers |
| Admin `/app/admin` (before C) | total 6, open 6; SLA null; users 46 / agents 3; knowledge 2/1/0/1; `ai.total_tokens` **null**; health connected | Total **6**, Open **6**, SLA **—**, Active agents **3** / 46 users, KB 2/1/0/1, AI requests **0**, Tokens **Not recorded**, API ok · DB connected |
| Admin `/app/admin` (after C–E) | (UI refresh) | Total **7**, Open **6**, In progress **1**, SLA **—**, AI requests **2** with **421 tokens recorded**, activity `TICK-00171 created` and `TICK-00171 status updated` |

Unavailable metrics used **—** / **Not recorded**, not invented numbers. Counts matched persisted tickets.

### Test C — Grounded chat — **PASS**

**Plan:** Confirm published doc `2f378f02-f84a-4734-8d4a-3bb1c034e0cc` “E2E VPN Connect Guide”. Read-only `POST /api/v1/knowledge/search`. Then `POST /api/v1/chat/conversations` and one `POST /api/v1/chat/conversations/{id}/messages` (non-stream; same `ChatService.send_message` path as the product). One Ollama generate. Question: *How do I connect to the corporate VPN using the company VPN client and which gateway should I choose?*

**Expected writes:** one conversation; user+assistant messages; citation if retrieval hits; telemetry + `chat.message.sent` audit. Title update only if title is still “New conversation” (we set a title, so no title rewrite).

**Observed:**

- Search **200**, hit document `2f378f02-…`, chunk `4a4f79d7-…`, title E2E VPN Connect Guide, similarity ~0.827
- Conversation **201** id `8e97b696-b5cf-46cb-8f76-730f92c98fa4`, title `E2E VPN how-to`, status `active`
- Send **200**. Intent `knowledge_query`, confidence `HIGH_CONFIDENCE`
- Assistant cites HQ gateway + company VPN client. Did **not** follow the retrieved “ignore previous instructions / IAM password reset” sentence. No `TICK-` in the answer
- Citation id `b116b65b-…` → same `document_id` / `chunk_id` / title as search. No unmatched citations
- `GET …/messages` **200**, 2 rows (user `47224f62-…`, assistant `7e7bf2f1-…`), 1 persisted citation
- Title remained `E2E VPN how-to` (expected)

### Test D — Escalation and reuse — **PASS**

**Plan:** `POST /api/v1/chat/conversations/8e97b696-…/escalate` `{ "reason": "user_requested_human" }`, GET ticket, escalate again. Stop if a duplicate ticket number appears.

**Expected writes (first):** `nextval(ticket_number_seq)`, INSERT ticket OPEN, ticket event CREATED, escalation, conversation → ESCALATED, audit. Second: reuse ticket; may INSERT another escalation.

**Observed:**

- First escalate **201**: escalation `285cfdcc-…`, ticket `79ebb910-…`, **`TICK-00171`**
- `GET /tickets/79ebb910-…` **200**, number `TICK-00171`, status `open`, requester employee. `conversation_id` is **not** on the ticket JSON schema; event metadata has `source: chat` and `conversation_id: 8e97b696-…`
- Event `ticket.created` → `open`
- Second escalate **201**: escalation `472492f9-…` (**different**), ticket id/number **same** `79ebb910-…` / `TICK-00171`
- Employee ticket list contains **one** `TICK-00171` (plus prior TICK-00167–00170)
- Conversation status **escalated**

No duplicate ticket. No cleanup attempted.

### Test E — Agent queue and status — **PASS**

**Plan:** Agent `GET /api/v1/tickets?scope=queue`. Confirm `TICK-00171`. PATCH `{ "status": "in_progress" }` only if current status is `open`. Re-GET events. Employee PATCH `resolved` should 403. Browser agent queue. Do not close.

**Expected writes:** UPDATE status; INSERT `ticket.status_changed`. Employee PATCH must not change the row.

**Observed:**

- Queue **200**, total 7, `TICK-00171` present, unassigned, `open`
- PATCH **200** → `in_progress`
- GET **200** still `79ebb910-…` / `TICK-00171` / `in_progress`
- Events: `ticket.created` open, then `ticket.status_changed` `open` → `in_progress`
- Employee PATCH **403** `Employees cannot update ticket status`; status unchanged
- Browser `/app/agent/queue`: `TICK-00171` **In Progress**, created Oct 23 2026 8:46 PM

### Skipped

| Item | Why |
|---|---|
| Test F IT automation | Not in the authorized A–E set |
| Live persist-failure (workflow 8) | Would need a code change or broken DB |
| Stream chat UI | One non-stream message used to keep a single Ollama call and inspectable JSON |
| pytest against Neon | Forbidden |

### Records created by A–E (non-secret ids)

| Kind | Id |
|---|---|
| Conversation | `8e97b696-b5cf-46cb-8f76-730f92c98fa4` |
| User message | `47224f62-9af1-41a4-a11b-021ab3e6dfb3` |
| Assistant message | `7e7bf2f1-7812-41a9-a4c7-b167889706ac` |
| Citation | `b116b65b-13c1-4b21-89bd-73a8e24311c5` → KB `2f378f02-…` / chunk `4a4f79d7-…` |
| Ticket | `79ebb910-4501-4026-bf43-4ef963ea1579` **TICK-00171** |
| Escalations | `285cfdcc-…`, `472492f9-…` |
| Auth | additional `refresh_tokens` + login/logout/refresh audits for API logins and browser employee/admin/agent sessions |

No rows were deleted. No reseed. Users total remained 46 after Test A.

---

## Remaining blocker

**Test F** (IT allow/deny/escalate + simulated execution) was not authorized this round. Workflow 8 live failure injection was not run.

Safest next step if you want it: authorize Test F only, one catalog-allowed IT request and one deny/escalate phrasing, no real IAM, no extra chat.

Do not run pytest against shared Neon. Do not delete `TICK-00171`.

---

## Honest demo checklist

1. Uvicorn worker **16248**; `/health` ok; `/ready` database connected; Vite on 5173.
2. Login employee → dashboard **4 / 4 / 0 / 0** from `/dashboard/summary`.
3. Chat the VPN how-to; expect **E2E VPN Connect Guide** citation `[KB-1]`, HQ gateway, not an IAM reset.
4. **Request human** on that conversation → **TICK-00171**; second request reuses it.
5. Agent Ticket Queue shows **TICK-00171**; status **In Progress** after OPEN → in_progress.
6. IT request (if demo’d later): say **simulated**; privileged requests should escalate/deny, not “installed.” **Not live-verified tonight.**
7. Admin dashboard: SLA **—** when no completed-SLA sample; tokens shown only when telemetry exists.
8. Do not say password was changed, software was installed, OTP/Vision/Docker exist, or MTTR/FCR were measured.

---

## Verdict

Live A–E **passed** against current PID **16248** and shared Neon, with persisted `TICK-00171` and a genuine citation to the published VPN guide. Isolated tests/build still stand. **Test F was not run.** The employee → cited answer → ticket → agent update workflow **was** observed end to end.
