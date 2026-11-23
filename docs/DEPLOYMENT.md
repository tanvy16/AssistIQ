# AssistIQ production configuration

## Required environment

| Variable | Notes |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | `postgresql+asyncpg://...sslmode=require` |
| `JWT_SECRET_KEY` | 32+ random characters |
| `COOKIE_SECURE` | `true` (required in production) |
| `CORS_ORIGINS` | Explicit frontend origins, never `*` |
| `LLM_API_KEY` | Optional; LLM generation fails safely if unset |

## Database

```powershell
cd backend
alembic upgrade head
```

Current head: `0009_password_reset_workflow`. Phase 10 added no migration.

Backup: use Neon branching / point-in-time recovery. AssistIQ does not ship a custom backup agent.

## AI model registry

Alembic creates an empty `ai_model_registry`. On process start the API runs **insert-if-missing** initialization for:

- `local-logreg-v1`
- `local-mlp-v1`
- `openai-gpt4o-mini`
- `ollama-llama3.2`

Startup never overwrites an existing row (including `enabled=false` or a custom `model_name`). If initialization fails, the process logs a warning and continues serving other APIs.

Initialization is skipped when `PYTEST_CURRENT_TEST` is set or `APP_ENV=test`.

Use the CLI only to **intentionally reseed** those four keys (force-upsert, sets `enabled=true`):

```powershell
python scripts/seed_ai_models.py
```

## Process

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 18765
```

- `GET /health` — liveness, no database
- `GET /api/v1/ready` — database connectivity

Graceful shutdown disposes the async engine via FastAPI lifespan.

## Frontend

```powershell
cd frontend
npm run build
```

Serve `frontend/dist` behind HTTPS with `VITE_API_BASE_URL` pointing at the API. Rebuild after changing the API origin.

## Rate limits

Single-instance in-memory limiter. Multiple uvicorn workers do **not** share counters. Place a reverse proxy limiter in front if you scale out.

## What is not production-integrated

- Real IAM / password mutation
- Real software installation
- Distributed rate limiting
- Admin user CRUD UI
