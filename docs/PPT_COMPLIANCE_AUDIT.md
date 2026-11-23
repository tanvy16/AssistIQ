# AssistIQ PPT promise vs implementation audit

**Presentation inspected:** `assisstai/AssistIQ_Review1_PPT.pptx` (11 slides; APA7 copy is the same deck). Title in the college problem statement: **“Autonomous AI Agent for IT Helpdesk.”** Product name on slide 2: **AssistIQ: An Autonomous GenAI-Powered Enterprise IT Helpdesk Platform.**

**Audit date:** 23 Oct 2026  
**Scope:** code inspection + **safe isolated tests only**. Application code was **not** modified during this audit.  
**Documents cross-checked:** `docs/SUBMISSION_STATUS.md`, `README.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md`. Those docs are **not** treated as proof.

**Counting method:** each numbered row in Section 3 is one requirement. Unverified end-to-end paths are **PARTIAL** or **BLOCKED**, never **PASS**. Mocks that are honest in code are not counted as real execution.

---

## 1. Executive summary and overall verdict

**Overall verdict: READY WITH DISCLOSURES**

AssistIQ is a real local IT helpdesk application: React + FastAPI, Neon tickets/chat/KB metadata, Chroma retrieval, LangGraph routing, streamed chat, and **simulated** password/software/access workflows. That is a defensible academic mini-project **if the PPT is presented as a Review-1 proposal plus a later implementation that deliberately uses sandbox IAM/execution**.

It is **not** the autonomous L1 agent described on slides 4 and 8:

- It does **not** resolve password resets, software installs, or access requests without humans in a real IAM/MDM sense.
- It does **not** implement OTP, Vision AI, Docker Compose, PDF/DOCX ingestion, or a public GitHub history.
- “Multi-agent” is **one LangGraph** with nodes, not four independent Diagnostic / Knowledge / Automation / Ticket agents.
- Adaptive routing by complexity, latency, cost, and privacy is **not** implemented.
- MTTR, deflection, and FCR are **not** product metrics.

`docs/SUBMISSION_STATUS.md` is largely consistent with the code. It is **optimistic** on chat→ticket: isolated tests pass, but the live API process was not restarted after that change, and Neon HTTP tests were not run.

---

## 2. PPT source (what was actually promised)

Extracted from Review-1 slides (not examiner imagination):

| Slide | Claim |
|---|---|
| 4 | Autonomous agent that resolves **password resets, software installs, access requests without human involvement** |
| 4 | Multi-agent AI; RAG; **secure OTP-gated automation**; human escalation; reduce **MTTR** |
| 6 | React+TS+Tailwind; FastAPI; SSE; **LangGraph + LangChain**; Chroma+embeddings+LLM APIs; PostgreSQL; **JWT+RBAC+OTP**; automation targets; **Vision: multimodal LLM/OCR**; **Docker Compose** |
| 7 | OpenAI/Gemini/Claude; Docker Desktop; **Sandbox Identity Adapter for Review-1 (no live AD)** |
| 8 | Objectives: automate L1 password/software/access; RAG+citations; **OTP+RBAC**; escalate low-confidence; open stack; **measure MTTR & deflection**. Flow: Intent Agent → RAG / **Vision** / Automation → Resolve **OR** create ticket |
| 9 | Wave B includes **Vision**; Wave C includes **Docker** |
| 5 | Public GitHub `https://github.com/<your-username>/AssistIQ` with commit history |

Slide 7’s sandbox-IAM assumption **matches** the implementation. Slides 4 and 8’s “without human involvement” / OTP / Vision / MTTR **do not**.

---

## 3. Compliance matrix

Status key: **PASS** / **PARTIAL** / **FAIL** / **NOT IMPLEMENTED** / **BLOCKED**.

“Safe to claim completed?” means **in the viva**, not “exists as a file.”

### A. ITSM core and ticket lifecycle

| ID | PPT / requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| A1 | Employee, IT Agent, Admin roles | **PARTIAL** | `backend/app/models/enums.py` `UserRole`; `frontend/src/lib/navigation.ts`; `App.tsx` | Roles exist in model, nav, and route guards. `navigation.test.ts` **36/36 frontend suite PASS**. Neon role HTTP tests **not run**. | Yes as “three roles in the app,” not as “RBAC proven on live DB this audit.” | Run isolated auth tests on a private DB later. |
| A2 | Auth, JWT, password hashing, backend RBAC | **PARTIAL** | `security.py` bcrypt+JWT; `deps.py` `get_current_user` / `require_roles`; `api/v1/auth.py` | Hashing and JWT are real. Admin-only routers: audits, observability, KB write, AI toggle. Login/logout tests use Neon — **skipped**. Hardening cookie/CORS unit tests **PASS**. | Yes for architecture; do not claim “auth tests passed on Neon today.” | Dedicated test DB. |
| A3 | Role dashboards and protected routes | **PARTIAL** | `App.tsx` `ProtectedRoute`; dashboards under `frontend/src/pages/*` | Frontend routes are role-split. Server still enforces ticket/conversation ownership in services. Live login **BLOCKED** this audit (would write audit rows). | Yes for UI structure. | — |
| A4 | Ticket create, category, priority, transitions, assign, comments, history | **PARTIAL** | `ticket_service.py` `VALID_STATUS_TRANSITIONS`; `api/v1/tickets.py`; `tests/test_tickets.py` | Full lifecycle is implemented. `test_tickets.py` **mutates Neon — not run**. | Demo if data already exists; do not say “HTTP tests passed today.” | Isolated DB. |
| A5 | SLA policy, deadlines, timers, breach, escalation | **PARTIAL** | `sla_policies` migration `0004_ticketing.py`; `sla_service.py`; `frontend/src/lib/sla.ts`; `ticket_service.ticket_stats` `sla_breached` | Due timestamps and UI overdue/due-soon **unit tests PASS**. Breach **count** is SQL. **No** automatic ticket escalation on SLA breach. `test_sla_service.py` uses Neon — **not run**. | Claim “SLA due dates and overdue badges,” not “SLA auto-escalation.” | Optional job to escalate overdue tickets (P2). |
| A6 | Chat-to-ticket and human escalation | **PARTIAL** | `ensure_ticket_for_conversation`; `agents/nodes/escalate.py`; `create_support_ticket.py`; `chat_service.escalate_conversation`; `ChatPage.tsx` | Isolated `test_chat_ticket_persistence.py` **PASS**. Live chat **not** sent (would write Neon). Running uvicorn PID from earlier may **not** include this code until restart. | After **API restart**, demo Request human → `TICK-#####`. Disclose “new path, unit-tested, not Neon-certified.” | Restart API (needs your approval). Unique index (P1). |
| A7 | Ticket IDs only after persistence | **PARTIAL** | escalate node / ChatPage toast require `ticket_number`; failures say “could not create” | Isolated failure test does not claim `TICK-`. Live path **BLOCKED**. | Yes as code behavior. | Restart API then one approved chat. |
| A8 | Repeated escalation duplicates | **PARTIAL** | `ensure_ticket_for_conversation` SELECT by `conversation_id` | Reuse is application-level. Isolated reuse test **PASS**. Race possible. | Say “same conversation reuses a ticket in the happy path,” not “duplicates impossible.” | Unique constraint. |
| A9 | DB constraints + concurrency protect idempotency | **FAIL** | `0004_ticketing.py` `conversation_id` nullable, **no unique**; no `SELECT FOR UPDATE` | Constraint requirement is not met. Concurrent POSTs can insert two tickets. | **Do not claim** DB-enforced idempotency. | Alembic unique index. |

### B. Knowledge management and RAG

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| B1 | PDF and DOCX upload/ingestion | **NOT IMPLEMENTED** | `api/v1/knowledge.py` JSON `body`; no `UploadFile` | Zero PDF/DOCX handling in backend/frontend. | **No.** Knowledge is **paste/type text**. | P1 if PPT still lists documents as files. |
| B2 | Lifecycle, chunk, embed, metadata, Chroma | **PARTIAL** | `knowledge_base_service.py`; `chunking_service.py`; `embedding_service.py` `hash-v1`; `adapters/chroma.py`; migration `0005` | Draft/publish/archive exist. Chunk+hash embed+Chroma unit tests **PASS**. Publish-on-Neon **not run**. Embeddings are **not** a neural model. | Claim “text KB → chunks → hash vectors → Chroma,” not “document upload pipeline” or “OpenAI embeddings.” | Optional neural embedder (P2). |
| B3 | Retrieval uses published only | **PARTIAL** | `search_published` `where status=published` + SQL join | Code filters published. Neon search tests **skipped**. | Yes as design. | — |
| B4 | Answers grounded in retrieved docs | **PARTIAL** | `prompts.py`; `generate_answer.py`; `confidence_check.py` | Prompt orders DATA-only. LLM can still ignore instructions. Live cited VPN answer is **historical**, not this audit. | Claim “retrieval + DATA prompt + citations when chunks exist,” not “hallucination-proof.” | — |
| B5 | Citations identify real chunks | **PARTIAL** | `retrieve_context.py`; `citation_check.py`; `MessageCitation` | Citations built only from retrieved rows with `document_id`/`chunk_id`. Fabrication filter drops incomplete rows. E2E **not run**. | Yes if a published doc is already indexed. | — |
| B6 | Empty retrieval / vector store failure | **PARTIAL** | `retrieve_context` catches `KnowledgeError` → `[]`; confidence `NO_EVIDENCE` | Isolated chroma-fail test **PASS**. | Yes: empty/limited-evidence, not fake sources. | — |
| B7 | Untrusted retrieved text / prompt injection | **PARTIAL** | `SYSTEM_INSTRUCTIONS`; `test_rag_prompt_treats_retrieved_text_as_data` **PASS** | Prompt-level control only, not a sandbox. | Yes as “retrieved text labeled DATA.” | — |
| B8 | Full upload → extract → index → cited answer | **PARTIAL** | Text create/publish exists; no file extract | Text path implemented; file path absent; live cited chat **BLOCKED**. | **No** as a document-upload demo. | PDF later (P1/P2). |

### C. AI chat and multi-agent architecture

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| C1 | Intent detection/classification | **PARTIAL** | `detect_intent.py` keywords then optional `LIGHTWEIGHT_ML` | Keyword map is real. ML adapter is keyword-scoring, not a trained logreg. Chat HTTP intent tests **skipped**. Routing unit tests **PASS**. | “Keyword intent + optional local scorer,” not “trained classifier.” | — |
| C2 | Diagnostic, Knowledge, Automation, Ticket **agents** | **FAIL** | `chat_graph.py` single graph; nodes not four agent services | PPT “Intent Agent → RAG / Vision / Automation” overstates. Nodes: `detect_intent`, `retrieve_context`, `start_it_request`, `start_password_reset`, `create_support_ticket`, `escalate`. No Diagnostic agent. No Vision agent. | **Do not** say four autonomous agents. Say **one LangGraph workflow with specialized nodes**. | Rename slides (P0 disclosure). |
| C3 | LangGraph nodes, routing, edges | **PARTIAL** | `chat_graph.py`, `it_request_graph.py`, `password_reset_graph.py`; `INTENT_ROUTE_MAP` | Graphs compile in process. Isolated route assertions **PASS**. Full graph+DB **not run**. | Yes as LangGraph orchestration. | — |
| C4 | Conversation state/history | **PARTIAL** | `CHAT_HISTORY_LIMIT`; `_load_history`; `Conversation` model | Implemented. Persist tests Neon **skipped**. | Yes in demo if chat works. | — |
| C5 | Token streaming FE+BE | **PARTIAL** | `chat.py` SSE; `LLMAdapter.stream_text`; `sendChatMessageStream` | Code path is complete. `test_send_message_stream_emits_tokens` mocks LLM and writes Neon — **not run**. Historical live stream exists from earlier sessions, not this audit. | “Streaming is implemented”; do not cite a live TTFT from today. | Optional approved smoke after restart. |
| C6 | Model abstraction + **adaptive** routing (complexity, confidence, latency, cost, privacy) | **FAIL** | `AdapterFactory`; `chat_service._resolve_generation_model_id` prefers `LLM_PROVIDER` then first LLM; intent may use first LIGHTWEIGHT_ML | Three adapter **types** exist (keyword ML, hash “DL”, LLM). **No** router uses complexity/latency/cost/privacy. DL is softmax over hash embeddings, not a neural net. | Claim “pluggable ML/DL/LLM adapters.” **Do not** claim adaptive routing. | P2 research, not demo-critical. |
| C7 | Working vs simulated “agents” | **PARTIAL** | See C2–C6 | LangGraph nodes = working functions. Mock IAM/execution = simulated. Vision = absent. Analysis only; not a product feature. | Disclose in viva. | — |
| C8 | Failures / low-confidence honesty | **PARTIAL** | `confidence_check.py`; ChatPage errors | `NO_EVIDENCE` appends a note and suggests human help; it does **not** auto-create a ticket. Model failures map to user-visible errors in generate/stream. | Claim “low evidence is labeled”; not “auto-escalates.” | Optional auto-escalate (P2). |

### D. Automation and security controls

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| D1a | Password reset workflow | **PARTIAL** | `password_reset_service.py`; `MockIAMAdapter`; graphs | Session email verification + mock reset. Neon HTTP tests **skipped**. Isolated policy/IAM design inspected. UI copy: mock IAM. | Demo as **simulated** reset only. | — |
| D1b | Account unlock | **NOT IMPLEMENTED** | no unlock route/model | — | **No.** | P2 |
| D1c | VPN restore automation | **NOT IMPLEMENTED** | VPN is a **knowledge** keyword only | No restore runbook. | “VPN **guides** via RAG,” not restore. | P2 |
| D1d | Software installation | **PARTIAL** | `MockExecutionAdapter` `simulated: True`; IT request graph | Isolated policy+mock tests **PASS**. Does not install software. Neon workflow tests **skipped**. | Simulated catalog install **only**. | — |
| D1e | Access-request workflow | **PARTIAL** | same IT request path; privileged → escalate | Isolated escalate-on-admin-privileges **PASS**. | Simulated / human-reviewed. | — |
| D2 | OTP verification | **NOT IMPLEMENTED** | `password_verification.py` matches **session email**, not OTP | No OTP model, SMS, or TOTP. PPT slides 4/6/8 require OTP. | **No. Disclose explicitly.** | P1 slide correction or real OTP (out of scope for tonight). |
| D3 | Risk, policy, approvals, RBAC, human escalation | **PARTIAL** | `policy_service.py`; password policy/risk; IT approvals | Isolated `test_it_policy.py` **PASS**. Neon approval HTTP **skipped**. | Yes as policy engine + mock execute. | — |
| D4 | Real execution vs sandbox | **PASS** (honesty) | `MockIAMAdapter`, `MockExecutionAdapter`; `SECURITY.md` | Returns `simulated: true`. Future adapters raise `NotImplementedError`. Isolated mock tests **PASS**. | **Must** say simulated. That matches PPT slide 7 sandbox assumption, **not** slide 4 “without human involvement.” | — |
| D5 | Mock cannot be mistaken for real change | **PARTIAL** | frontend `MOCK_IAM_LABEL`, `MOCK_IT_EXECUTION_LABEL`; observability tests **PASS** | Labels exist on observability. Chat/IT request UIs also explain simulation (`itRequests.ts`). | Show the mock banner during demo. | — |
| D6 | Secrets, bypass, authz, validation, exposure | **PARTIAL** | `json_safe`; 500 generic detail; audit sanitize; `FORBIDDEN_KEYS` on IAM | Unit `json_safe` **PASS**. Full auth/rate-limit HTTP tests **skipped**. `.env` not printed. | Do not claim a security audit certification. | — |
| D7 | Employee invoking privileged tools via API | **PARTIAL** | Catalog/runbook PATCH `require_roles(ADMIN)`; execute only after policy | Employees can **submit** catalog software requests; policy may ALLOW mock execute. They cannot enable runbooks or skip verification via documented APIs. `force_allow` rejected in password tests (Neon, not re-run). | “Employees cannot admin-toggle catalogs.” They **can** trigger **mock** allowed installs. | — |
| D8 | Real IAM / real password changes | **NOT IMPLEMENTED** | MockIAM never writes `User.password_hash` | By design. | **No.** | Do not build real IAM for this viva. |

### E. Vision AI

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| E1 | Screenshot upload/capture | **NOT IMPLEMENTED** | no image routes/components | Frontend grep: no screenshot/vision. | **No.** | P2 / slide removal. |
| E2 | Error-dialog / UI-state image analysis | **NOT IMPLEMENTED** | — | — | **No.** | — |
| E3 | Vision model or OCR API | **NOT IMPLEMENTED** | LLM adapter is chat-completions text | — | **No.** | — |
| E4 | Structured vision results in troubleshooting | **NOT IMPLEMENTED** | — | — | **No.** | — |
| E5 | Vision error handling / security | **NOT IMPLEMENTED** | nothing to secure | Placeholder would still be NOT IMPLEMENTED. | **No.** | — |

### F. Governance, auditability, observability

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| F1 | Audit events for security-sensitive and ticket changes | **PARTIAL** | `audit_events` `0003`; `record_audit_event`; ticket_events; IT/password events | Code writes events. Neon audit tests **skipped**. | “Append-only application audit log.” | — |
| F2 | Durable; unauthorized modification blocked | **PARTIAL** | `GET /audits` admin-only; **no** PATCH/DELETE API | Anyone with DB credentials can `UPDATE` rows. Not WORM/immutable. | Not “immutable audit trail.” | P2 |
| F3 | Retrieval scores and citations | **PARTIAL** | `ChatInteractionTelemetry`; `MessageCitation` | Stored when chat persists. Neon chat tests **skipped**. | Yes if you show a cited message already in DB. | — |
| F4 | Latency, tokens, cost, errors | **PARTIAL** | `AIInferenceTelemetry`; observability service “never fabricates”; Recharts on admin observability | Cost/tokens **null** when provider omits them; UI shows "—" / Unknown. Volume/outcomes/latency/model charts map `usage.over_time`, `usage.counts`, `latency.over_time`, `models[]` (`chartSeries.test.ts` + `observability.test.ts` **PASS**, 23 Oct evening). A single daily bucket is not drawn as a time series. Live admin observability page **not** opened (current browser session is agent). | “Telemetry when the provider reports it; charts hide rather than invent history.” | — |
| F5 | MTTR, deflection, FCR, SLA compliance analytics | **NOT IMPLEMENTED** (MTTR/FCR/deflection); **PARTIAL** (SLA breach **count**) | no mttr/fcr/deflection in `app/` | PPT objective 6 unmet. `sla_breached` is a dashboard integer, not a compliance report. | **Do not** quote MTTR/FCR/deflection as AssistIQ results. | P1 slide fix. |
| F6 | Dashboard from persisted data vs hardcoded | **PARTIAL** | `dashboard_service.py` SQL aggregates | No hardcoded live metrics found on employee/admin dashboards. Neon dashboard tests **skipped**. | Yes as “SQL aggregates,” unverified live. | — |
| F7 | Null/empty, windows, definitions | **PARTIAL** | observability `24h/7d/30d/custom`; empty copy | Frontend tests for empty/unknown **PASS**. Missing request-volume days in the selected window are zero-filled; latency days are **not** zero-filled. Unevaluated models stay **Not evaluated**. | Yes. | — |
| F8 | Immutable audit trail | **FAIL** vs strong PPT “audit trail” if sold as tamper-proof | JSONB `audit_events` | Ordinary table. | Disclose. | — |
| F9 | Production-grade AI observability | **PARTIAL** | in-process telemetry + admin page + Recharts | Academic dashboard with real API-backed charts where series exist. Backend still `date_trunc("day")` (no hourly history). Not Datadog/OpenTelemetry. | “Academic operational dashboard with recorded daily telemetry.” | — |

### G. Architecture, integrations, UI

| ID | Requirement | Status | Sources | Evidence | Safe to claim completed? | Smallest fix |
|---|---|---|---|---|---|---|
| G1 | React ↔ FastAPI | **PARTIAL** | Vite `VITE_API_BASE_URL`; `npm run build` **PASS** | 23 Oct evening build **722 modules** (Recharts). Live agent dashboard/tickets/chat canvas `#111311`, nav `#171A17` verified in browser. | Yes that the client is a real SPA calling the API. | — |
| G2 | Neon PostgreSQL + migrations | **PARTIAL** | Alembic `0001`–`0009`; `DATABASE_URL` required | Head `0009_password_reset_workflow`. Live `alembic current` **not** run (would use secrets/DB). | “Migrations exist through password-reset.” | — |
| G3 | Chroma + embeddings | **PARTIAL** | hash-v1 384-d; local Chroma tests **PASS** | Not LLM embeddings. | Hash embeddings, not “LLM APIs” for retrieval. | — |
| G4 | Ollama / model config / fallback | **PARTIAL** | `.env.example` Ollama `/v1`; prewarm `/api/generate`; chat `/chat/completions` | Isolated prewarm tests **PASS**. Historical prewarm HTTP 200 on 23 Oct. Chat fallback is error text, not a second model. | Local Ollama is the configured path; OpenAI/Gemini/Claude are **not** required at runtime. | — |
| G5 | Error / loading / empty / success-error copy | **PARTIAL** | `EmptyState`, `LoadingState`, toasts | Present on dashboards/chat. Not all pages exhaustively clicked. | Reasonable for demo. | — |
| G6 | UI actions hit backend | **PARTIAL** | `tickets.ts`, `chat.ts`, `itRequests.ts`, `passwordResets.ts` | Fetch wrappers exist. No local-only fake ticket create found. | Yes. | — |
| G7 | Contract / stale / authz / config failures | **PARTIAL** | chat 400 on stale model id (prior work) | Config-dependent: missing Ollama → generation errors; missing SLA policies → chat ticket create fails honestly. | Disclose Ollama + SLA seed needed. | Restart API; confirm SLA rows exist without querying secrets. |
| G8 | LangChain as orchestration | **PARTIAL** | `requirements.txt` `langchain-core`; **no** `import langchain` in `app/` | LangGraph is used. LangChain stack claim is overstated. | “LangGraph,” not “LangChain agents.” | Remove unused dep later (P2). |
| G9 | Docker Compose | **NOT IMPLEMENTED** | no Dockerfile/compose | PPT slides 6/9. | **No.** | P2 |
| G10 | Public GitHub + commit history | **NOT IMPLEMENTED** | `git status` untracked; PPT placeholder URL | No commits, no origin required for this machine. | **No.** | Init remote if the college requires it (P0 for Review-1 checklist, not for running the app). |

### H. Stated objectives (user brief + PPT slide 8)

| ID | Objective | Status | Notes | Safe to claim completed? |
|---|---|---|---|---|
| H1 | Integrated ITSM core with authoritative RBAC | **PARTIAL** | Real tickets/roles/server checks; Neon auth tests skipped | Yes with “not re-tested on shared DB today.” |
| H2 | Structured ticket lifecycle with SLA awareness | **PARTIAL** | Transitions+SLA due dates; no auto-escalate | Yes for lifecycle+due dates. |
| H3 | Knowledge-grounded retrieval over published content | **PARTIAL** | Text KB + Chroma + DATA prompt; no PDF; live RAG skipped | Yes if a published doc already exists. |
| H4 | Adaptive multi-level AI/model-routing | **FAIL** | Adapters exist; routing is not adaptive | **No.** |
| H5 | Secure, auditable, measurable AI-assisted ops | **PARTIAL** | Mock automation + app audits + telemetry; not OTP/MTTR/FCR/immutable log | “Auditable simulated L1,” not “production SOC.” |
| H6 | PPT: automate L1 without humans | **FAIL** | Mock + HITL + no real IAM | **No.** Align with slide 7 sandbox wording. |
| H7 | PPT: OTP + RBAC | **PARTIAL** | RBAC yes; OTP no | Split the claim. |

---

## 4. Tests executed and results

| Command | Result |
|---|---|
| Isolated backend pytest (prewarm, default models, chat-ticket persistence, IT policy, chunking, embeddings, Chroma tmp, selected hardening units) | **56 passed**, 1 chromadb deprecation warning, exit 0 |
| `cd frontend; npm test` | **9 files, 36 tests passed** |
| `cd frontend; npm run build` | **tsc -b && vite build** exit 0; 122 modules |

A first pytest invocation **incorrectly included** `tests/test_sla_service.py` (Neon). That process was **stopped before completion** so shared SLA rows would not be inserted. No SLA HTTP/DB tests were completed.

## 5. Tests not executed (and why)

| Tests | Reason |
|---|---|
| Full `pytest` | `conftest.py` uses `DATABASE_URL` and fixtures **commit/delete** on shared Neon |
| `test_tickets.py`, `test_chat.py` HTTP, `test_auth.py`, `test_it_requests.py`, `test_password_reset.py`, `test_knowledge.py`, `test_observability.py`, `test_hardening` client tests | Insert/delete users, tickets, chats, KB |
| `test_sla_service.py` | `sla_policies` fixture **commits** policies |
| Live AssistIQ chat / escalate / IT execute | Writes Neon; may call Ollama |
| `alembic current`, `/health` this audit | Not required; health would be an HTTP call (API may still be up from earlier) |

## 6. End-to-end vs unit vs inspection

| Workflow | Verification level |
|---|---|
| Frontend production build | **Build PASS** |
| SLA badge math | **Frontend unit PASS** |
| Hash embed + Chroma add/search | **Unit PASS** (tmp dir) |
| RAG DATA prompt | **Unit PASS** |
| Chat ticket helper / escalate node / intent route | **Unit PASS** (mocked DB) |
| IT policy allow/deny/escalate + mock adapter | **Unit PASS** |
| Prewarm 2xx vs 404/timeout | **Unit PASS**; one **historical** live 200 on 23 Oct |
| Employee login → chat → cited answer | Inspection + **historical** session; **not this audit** |
| Request human → real ticket on Neon → agent queue | Code + unit; **live BLOCKED** (no chat write; API may be stale) |
| Password reset / software install real IAM/host | **Not implemented** (mock) |
| Vision screenshot troubleshooting | **Not implemented** |

---

## 7. Overstated or unsupported PPT (and doc) claims

1. **“Resolves password resets, software installs, and access requests without human involvement”** — false for real systems; mock + often HITL.
2. **OTP-gated automation** — not in the product.
3. **Vision / multimodal LLM / OCR** — absent.
4. **Docker Compose** — absent.
5. **LangChain multi-agent** — LangGraph nodes only; `langchain-core` unused in `app/`.
6. **Measure MTTR and deflection** — not implemented as metrics.
7. **Four agents (Intent / RAG / Vision / Automation)** — one graph; no Vision.
8. **Adaptive ML/DL/LLM routing on complexity/cost/privacy** — not implemented; “DL” is hash+softmax.
9. **Public GitHub with commit history** — placeholder; local repo has **no commits**.
10. **LLM APIs (OpenAI/Gemini/Claude) as the runtime AI stack** — local **Ollama** is what was configured and prewarmed.
11. **`SUBMISSION_STATUS.md` “Chat → real ticket” as live-verified** — isolated tests only; restart still required for the running API.

Slide 7 **sandbox identity adapter** is the claim that matches the code. Prefer that wording in the viva.

---

## 8. Prioritized remediation (do not implement until approved)

### P0 — demo / correctness / honesty

1. **Restart FastAPI** so chat escalation uses `ensure_ticket_for_conversation` (process on 18765 may still be the pre-change server).
2. **Correct the PPT script:** mock IAM/execution; no OTP; no Vision; no Docker; no MTTR/FCR; one LangGraph, not four agents.
3. **Do not demo “password was changed” or “VS Code was installed.”**

### P1 — promised functionality missing

1. Unique index on `tickets.conversation_id` (idempotency).
2. PPT/docs: OTP → “session email verification.”
3. PDF/DOCX only if the examiner expects file upload (not required for a text KB demo).
4. Public GitHub if Review-1 still requires it (college admin, not a product feature).

### P2 — future / optional

Vision, Docker, neural embeddings, real IAM, adaptive routing, MTTR/FCR dashboards, immutable audit, account unlock, VPN restore runbook.

---

## 9. What is safe to demonstrate vs what must be disclosed

**Safe to demonstrate (with the disclosures below):**

- Role-based UI (employee / agent / admin).
- Ticket list/detail/SLA overdue badge (existing data).
- AI chat against **published text** KB with citations **if** chunks exist; otherwise limited-evidence note.
- **Request human** / “create ticket” → `TICK-#####` **after API restart**.
- IT request for an allow-listed item → **simulated** execution banner.
- Password reset → email match verification → **simulated** IAM.
- Admin observability: mock labels, "—" for unknown tokens/cost; Recharts volume/outcomes/latency/model charts use recorded telemetry or an explicit empty state (not a blank heading). Live admin page not opened this pass (agent session; no Neon login switch).

**Must disclose:**

| Topic | Line to say |
|---|---|
| IAM / install | “Sandbox/mock adapters. No Active Directory. No host installs. No `password_hash` change.” |
| OTP | “Not implemented. Identity check is authenticated session + email confirmation.” |
| Vision | “Not in this build.” |
| Agents | “LangGraph nodes, not four separate agent runtimes.” |
| Embeddings | “Deterministic hash-v1, 384-d, not a vendor embedding API.” |
| Metrics | “We do not report AssistIQ MTTR, FCR, or deflection.” |
| GitHub | “Local tree; Review-1 GitHub URL was a placeholder.” |
| Chat tickets | “Persistence implemented and unit-tested; live Neon path not re-run this audit.” |

---

## Status counts

Each of the **68** matrix IDs (A 9 + B 8 + C 8 + D 12 + E 5 + F 9 + G 10 + H 7) has exactly one primary status.

| Status | Rows | IDs |
|---|---|---|
| PASS | 1 | D4 |
| PARTIAL | 48 | remaining implemented-but-incomplete-or-unverified rows |
| FAIL | 6 | A9, C2, C6, F8, H4, H6 |
| NOT IMPLEMENTED | 13 | B1, D1b, D1c, D2, D8, E1–E5, F5, G9, G10 |
| BLOCKED | 0 | live E2E is a **blocker inside PARTIAL** rows, not a primary status |
| **Total** | **68** | |

Completion **percentage is not a valid readiness score** here: 47 PARTIAL rows are not 69% done. Unverified and mocked work is not completed.

---

## Alignment with `docs/SUBMISSION_STATUS.md`

Mostly accurate. Adjust verbally:

- Chat→ticket is **unit-tested**, not Neon-verified.
- Running API may be **stale** until restart.
- Do not let “implemented and verified” be heard as “full pytest + live chat today.”
