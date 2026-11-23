# AssistIQ

AI-powered IT support platform: ticketing, knowledge/RAG chat, policy-controlled IT requests, simulated password reset, ticket analytics, admin observability, and TOTP multi-factor authentication.

**Submission documents:** `docs/FINAL_SUBMISSION_REPORT.md` (status, evidence, measurements) · `docs/DEMO_SCRIPT.md` · `docs/KNOWN_LIMITATIONS.md` · `docs/SECURITY.md`.

## Architecture

```
React + Vite (http://127.0.0.1:5173)
        ↓ REST + HttpOnly refresh cookie
FastAPI (http://127.0.0.1:18765)
        ├── Neon PostgreSQL (relational source of truth)
        └── ChromaDB (chunk vectors only)
```

Roles: `employee`, `agent`, `admin`. Backend RBAC is authoritative.

**Mock IAM is used; no real password is changed.**  
**Mock execution is used; no real software installation or system modification occurs.**

## Prerequisites

- Python 3.11+
- Node.js 20+
- A [Neon](https://neon.tech) project (asyncpg URL with `sslmode=require`)

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set at least `DATABASE_URL` and `JWT_SECRET_KEY` (32+ characters). Use `127.0.0.1` consistently in CORS.

```powershell
python scripts/check_db_connection.py
alembic upgrade head      # head = 0010_security_mfa (additive MFA / lockout / token-family tables)
```

`backend/requirements.txt` now includes `cryptography` (MFA secret encryption) and `segno` (QR codes); run `pip install -r requirements.txt` after pulling.

Security settings (optional in development, see `docs/SECURITY.md` §10): `MFA_ENCRYPTION_KEY` (**required when `APP_ENV=production`**), `MFA_ENFORCEMENT_MODE` (`grace` default outside production, `strict` in production), `MFA_REQUIRED_ROLES`, `LOGIN_LOCKOUT_*`.

Optional seeds (users, catalogs, SLA). AI models are **not** required here:

```powershell
python scripts/seed_users.py
python scripts/seed_it_catalogs.py
```

On normal startup (`APP_ENV` is not `test`, and pytest is not running) the API inserts the four default AI registry keys **only if they are missing**. Existing administrator toggles, providers, and model names are left unchanged. Test runs skip this step (`PYTEST_CURRENT_TEST` or `APP_ENV=test`).

To **force-restore** the packaged defaults (re-enables those four keys and overwrites their fields), run:

```powershell
python scripts/seed_ai_models.py
```

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 18765 --reload
```

- `GET /health` → liveness
- `GET /api/v1/ready` → database connected

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`.

### Ports

| Service | Port |
|---|---|
| API | `127.0.0.1:18765` |
| Vite dev server | `127.0.0.1:5173` (must be listed in `CORS_ORIGINS`) |
| Ollama | `127.0.0.1:11434` |

If another project already uses 5173, Vite moves to the next free port; that origin must then be added to `CORS_ORIGINS` (it can be passed as a process environment variable, e.g. `$env:CORS_ORIGINS='["http://127.0.0.1:5173","http://127.0.0.1:5174"]'`, without editing `.env`).

`LLM_PREWARM_ENABLED=false` skips the startup keep-alive generation (useful when generations must be counted); leave it on for demos so the model is loaded.

## Testing

Frontend (safe, no database):

```powershell
cd frontend
npm test
npm run build
```

Backend — **full suite on a disposable database** (requires Docker Desktop; never touches Neon):

```powershell
cd backend
.\scripts\run_isolated_tests.ps1                         # all tests
.\scripts\run_isolated_tests.ps1 tests/test_security_mfa.py -q
.\scripts\run_isolated_tests.ps1 -RemoveContainer       # delete the test container afterwards
```

The script starts a throwaway `postgres:16` container on `127.0.0.1:55433` with a random password, runs `alembic upgrade head`, and runs pytest with `DATABASE_URL` set only for that process.

Safety guard: `tests/conftest.py` skips every database-backed test (at collection time, before any fixture can run) unless `DATABASE_URL` points at a loopback database. Plain `pytest` with the Neon `.env` therefore runs only the pure unit tests and skips the rest — it can no longer insert or delete shared rows.

Submission evidence: `docs/FINAL_SUBMISSION_REPORT.md` (current) and the earlier `docs/SUBMISSION_STATUS.md`, `docs/PRE_SUBMISSION_CHECK.md`.

## Rate limits

In-memory, per-IP, configurable via `RATE_LIMIT_*` in `backend/.env`. Suitable for a single API process. See `docs/SECURITY.md` and `docs/DEPLOYMENT.md`.

## Security notes

- Never commit `backend/.env`.
- Frontend must not receive LLM keys, JWT secrets, or database URLs.
- Production: `APP_ENV=production`, `COOKIE_SECURE=true`, explicit CORS origins, HTTPS.

## Project docs

- `docs/FINAL_SUBMISSION_REPORT.md` — final status, test results, measurements, PPT compliance
- `docs/DEMO_SCRIPT.md` — 6-minute employee / agent / admin walkthrough
- `docs/KNOWN_LIMITATIONS.md` — simulated vs real, not-implemented items
- `docs/SECURITY.md` — MFA, tokens, RBAC matrix, audit events, keys, mock IAM/execution, RAG boundaries
- `docs/DEPLOYMENT.md` — production env, health, backups
- Design notes in `assisstai/` are reference-only
