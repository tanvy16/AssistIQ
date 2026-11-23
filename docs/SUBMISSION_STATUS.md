# AssistIQ submission status

Evidence-based snapshot for university demonstration. Claims below are limited to what was inspected and tested in this session.

## 1. Implemented and verified by evidence

| Feature | Evidence |
|---|---|
| Auth, JWT, refresh cookie, RBAC | Existing `backend/app/core/deps.py`, `ProtectedRoute`, admin-only `require_roles` on observability/audits/users/KB write/AI toggle. Full Neon login tests **not re-run** (would write audit rows). |
| Ticketing lifecycle APIs | Existing `ticket_service` + `tests/test_tickets.py` (uses shared Neon — **not re-run** this session). |
| Chat → **real ticket** persistence | New `ensure_ticket_for_conversation`. Isolated tests in `tests/test_chat_ticket_persistence.py` **PASS**. UI toast shows `ticket_number` only after API returns it. |
| Intent `ticket_creation_request` | Routes to `create_support_ticket` (no longer a generate-only path). Isolated route + node tests **PASS**. |
| Human escalation | Graph `escalate` node persists a ticket before claiming success. POST `/chat/conversations/{id}/escalate` creates ticket + escalation row. Isolated node tests **PASS**. |
| RAG as untrusted DATA | `SYSTEM_INSTRUCTIONS` + `test_rag_prompt_treats_retrieved_text_as_data` **PASS**. |
| Empty / failed retrieval | Chroma `KnowledgeError` in `retrieve_context` yields empty citations (no fabricated sources). Isolated test **PASS**. |
| Local LLM prewarm | 2xx-only success log, 45s read timeout. `tests/test_prewarm.py` **PASS**. One live startup on 2026-10-23 produced HTTP 200 then `prewarm completed` (does **not** by itself prove the model remains in RAM). |
| Mock IT automation | Policy engine + `MockExecutionAdapter` (`simulated: true`). Isolated `tests/test_it_policy.py` **PASS**. |
| Dashboards | Ticket/KB/user/AI counts from SQL (`dashboard_service`). Empty activity uses `EmptyState`. Token/cost UI uses "—" / "Unknown" when null. |
| Frontend unit tests | `npm test` — 36 passed. |
| Frontend production build | `npm run build` (see session log). |
| Ollama prewarm implementation | `backend/app/main.py` `_prewarm_local_llm`. |

## 2. Partial / unverified against a live database

- Employee create → agent assign → comment → resolve: implemented in code; Neon integration tests exist but were **skipped** this session to avoid mutating shared data.
- Streamed chat with real `llama3.2:latest`: previously demonstrated historically; **not** re-run this session (no extra inference).
- Knowledge publish → Chroma index → cited chat answer: implemented; local Chroma adapter tests **PASS**; full publish-on-Neon path not re-run.
- IT request and password-reset **end-to-end HTTP** tests use Neon fixtures — skipped. Mock adapters and policy unit tests **PASS**.
- PDF/DOCX upload: **not implemented**. Knowledge is title/body text via admin forms.

## 3. Known limitations

- Shared Neon is the test database; `pytest` without a path filter can insert/delete rows. Use isolated files listed in README.
- IAM and software execution are **mocks**. No Active Directory, no host installs.
- Hash embeddings (`hash-v1`), not a neural embedding model.
- Intent classifier is keyword-first, optional lightweight ML.
- In-memory rate limits (single API process).
- No unique DB constraint on `tickets.conversation_id` (idempotency is application-level lookup). No migration was added against shared Neon.
- Chat token counts may be null from Ollama; UI must not invent them.

## 4. Architecture and request flow

```
React (127.0.0.1:5173)
  → FastAPI (127.0.0.1:18765)
      → Neon PostgreSQL (tickets, chat, users, KB metadata, telemetry)
      → ChromaDB (chunk vectors only)
      → Ollama llama3.2:latest (generation, optional startup prewarm)
```

**Knowledge chat:** Frontend SSE → `send_message_stream` → history/DB → LangGraph (intent → retrieve → prompt) → Ollama stream → persist messages/citations.

**Escalation / create-ticket chat:** intent or Request-human button → `ensure_ticket_for_conversation` (flush ticket + `ticket.created` event) → honest answer/toast with `TICK-#####` only after persistence → agent queue sees unassigned OPEN ticket.

## 5. Setup / start commands

See repository `README.md`. Do not print `.env` values.

Typical demo (PowerShell):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 18765
```

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Ollama should already be serving on `11434` if local generation is required.

## 6. Tests run this session (safe / isolated)

| Command | Result |
|---|---|
| `pytest tests/test_prewarm.py tests/test_default_models.py tests/test_chat_ticket_persistence.py tests/test_it_policy.py tests/test_chunking_service.py tests/test_embedding_service.py tests/test_chroma_adapter.py` + selected `test_hardening` units | **55 passed** then RAG wording fix; focused re-run **31 passed** |
| `npm test` (frontend) | **36 passed** |
| `npm run build` | see build log |
| Full `pytest` / `test_tickets.py` / `test_chat.py` HTTP | **Not run** (shared Neon writes) |

## 7. Environment variable names only

`APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `RATE_LIMIT_*`, `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`, `EMBEDDING_MODEL_ID`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_DEFAULT_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `CHAT_*`, `SEED_*` (dev seeds).

## 8. Five-minute demo

1. Login as employee → Dashboard (real ticket counts or zeros).
2. Chat: ask a VPN/how-to question. If published KB exists, expect citations; if not, expect limited-evidence note — not invented sources.
3. Click **Request human** or type that you want to speak to an agent. Confirm toast includes `TICK-#####`.
4. Open **My tickets** and open that ticket.
5. Login as agent → Queue → assign/update the ticket.
6. Admin → Observability: mock IAM/execution labels; costs/tokens "—" when unknown.
7. Optional: IT request for VS Code — simulated execution only.

## 9. Remaining ~20% / future work

1. Isolated test database so full HTTP suites can run without shared Neon.
2. Unique constraint on `tickets.conversation_id`.
3. PDF/DOCX ingestion.
4. Neural embeddings and a stronger intent model.
5. Real IAM / software management adapters behind explicit approval (not for this demo).
6. Distributed rate limiting and production log aggregation.
7. Prompt prefix / system-role experiment for Ollama TTFT (not required for submission).
