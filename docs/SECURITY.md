# AssistIQ security and runtime assumptions

Updated 19 Nov 2026 (final submission sprint). Every control below states how it was verified. "Isolated" means the disposable Docker PostgreSQL test database (`backend/scripts/run_isolated_tests.ps1`); "live" means the shared Neon database during the authorised A–E run. Limitations are collected in `docs/KNOWN_LIMITATIONS.md` §3.

> This is an academic project. It has meaningful controls (TOTP MFA, hashed secrets, rotating refresh tokens, lockout, backend RBAC, audit logging) but it has **not** been penetration-tested and is not claimed to be "enterprise-grade".

---

## 1. Mock IAM

**Mock IAM is used; no real password is changed.**

Password reset confirmation calls `MockIAMAdapter` only. AssistIQ never writes `User.password_hash` during a reset and never talks to Active Directory, Okta, or another identity provider. (The *account* password change on the Security page, §6, is a different, real feature for the user's own AssistIQ login.)

## 2. Mock software / access execution

**Mock execution is used; no real software installation or system modification occurs.**

IT requests plan against allow-listed runbooks and execute through `MockExecutionAdapter`. There is no shell, PowerShell, or package-manager integration. Policy decides allow / deny / escalate; privileged access requests escalate to humans; nobody may approve their own request.

## 3. Authentication architecture

```
Browser (React)                       FastAPI                               PostgreSQL
───────────────                       ───────                               ──────────
POST /auth/login {email,password} ──▶ lockout check (auth_login_throttle)
                                      bcrypt verify (dummy hash for unknown emails)
                                      ├─ MFA enabled  ──▶ {mfa_required, mfa_token(5 min)}   no cookie, no access token
                                      ├─ role requires MFA, not enrolled, strict ──▶ {enrollment_token(15 min)}
                                      └─ otherwise ──▶ access JWT (15 min, mfa=false) + refresh cookie
POST /auth/mfa/verify {mfa_token, code|recovery_code}
                                      TOTP check (replay + lockout) ──▶ access JWT (mfa=true) + refresh cookie (mfa_verified)
any API call  Authorization: Bearer ─▶ get_current_user: signature, type=access, user active,
                                      role matches DB, and if user has MFA: token.mfa must be true
401 ──▶ authFetch: one shared POST /auth/refresh (cookie) ──▶ rotate ──▶ retry once; failure ends the session
```

| Item | Implementation | Verified |
|---|---|---|
| Password hashing | bcrypt (`bcrypt.gensalt()`, cost 12). Passwords > 72 bytes are rejected instead of crashing (bcrypt 5 raises). | Unit + isolated (`test_long_password_does_not_500`) |
| Unknown-email timing | A dummy bcrypt check runs for unknown/inactive users, so timing does not reveal which emails exist | Code inspection |
| Generic errors | Wrong password and unknown email return the identical `401 Invalid email or password` | Isolated (`test_login_lockout_and_generic_errors`) |
| Lockout | 5 failures in 15 min (per normalised email, existing or not) → 15 min lock → `429` with `Retry-After`, even for the correct password. Audited `auth.account_locked`, `auth.login_blocked_locked`. Configurable `LOGIN_LOCKOUT_*`. | Isolated |
| Rate limiting | Per-IP sliding window: login 30/min, refresh 60/min, MFA 10/min, plus chat/search/IT buckets | Existing + isolated |
| Password policy (change) | ≥ 12 chars, ≤ 72 bytes, 3 of 4 character classes, must not contain the email name, must differ from current. Mirrored client-side for feedback only. | Unit + isolated |

## 4. Multi-factor authentication (TOTP)

Compatible with Google Authenticator, Microsoft Authenticator and any RFC 6238 app (SHA-1, 6 digits, 30 s).

| Requirement | Implementation | Verified |
|---|---|---|
| TOTP algorithm | Standard-library RFC 4226/6238 implementation (`app/core/mfa.py`) | RFC 4226 and RFC 6238 test vectors (unit) |
| Unique secret per user | 160-bit random secret (`secrets.token_bytes(20)`) | Unit |
| QR enrollment | `otpauth://` URI rendered server-side to SVG (`segno`), shown with a manual setup key | Browser (isolated stack) |
| Enable only after verification | `start` stores a **pending** encrypted secret; MFA becomes enabled only when the first code verifies (`confirm_enrollment`). Pending enrollment expires after 15 min. | Isolated (`test_enrollment_requires_password_and_first_code`) + browser |
| Re-authentication | Enrollment start, recovery-code regeneration, disable and password change all require the current password; regeneration/disable/password change also require a current code | Isolated |
| Secrets at rest | Fernet (AES-128-CBC + HMAC-SHA256) ciphertext in `user_mfa.secret_encrypted`. The secret is returned **only** by `/auth/mfa/enroll/start` while enrollment is pending (`Cache-Control: no-store`), never afterwards, never logged. | Isolated (`test_secret_stored_encrypted_and_codes_hashed`, `test_no_secrets_in_logs_or_audit`) |
| OTP values | Never stored; only the last accepted time-step is stored | Code + isolated |
| Clock drift | ±1 step (±30 s) accepted; ±2 rejected | Unit |
| Replay prevention | Accepted step recorded in `last_used_step`; a code for an equal or earlier step is rejected | Unit + isolated |
| Brute-force | 5 wrong codes → MFA step locked 15 min (`429`), audited `mfa.locked`; plus 10/min per-IP rate limit | Isolated (`test_mfa_lockout_after_repeated_wrong_codes`) |
| Recovery codes | 10 codes, ~50 bits each, shown **once** (copy / download .txt), stored as HMAC-SHA256 hashes; each works once (conditional `UPDATE … WHERE used_at IS NULL`) | Isolated (`test_recovery_code_works_exactly_once`) + browser |
| Disable | Password + TOTP or recovery code; refused for MFA-mandatory roles in `strict` mode | Isolated |
| Bypass resistance | Challenge / enrollment tokens have their own `type` and are rejected by `get_current_user`; access tokens minted before enrollment (no `mfa` claim) are rejected once MFA is enabled; refresh tokens that never passed MFA cannot be renewed for an MFA account; enabling MFA revokes every other session | Isolated (`test_enrolled_user_cannot_bypass_mfa`, `test_strict_mode_requires_agent_enrollment_before_any_access`) |

### Enforcement policy

| Setting | Default | Meaning |
|---|---|---|
| `MFA_REQUIRED_ROLES` | `["admin","agent"]` | Roles that must use MFA. Add `"employee"` for organisation-wide enforcement. |
| `MFA_ENFORCEMENT_MODE` | `strict` when `APP_ENV=production`, otherwise `grace` | **strict:** a required-role user without MFA receives only a 15-minute enrollment token after the password step and cannot reach any other API until enrolled. **grace:** the user signs in normally but `/auth/me` reports `mfa_enrollment_required` and the UI shows a persistent banner linking to Security. |

`grace` is the development default so the shared seeded demo accounts are not locked out unexpectedly. Migration strategy for a real rollout: announce → run in `grace` while privileged users enroll (Admin › Users shows "MFA coverage x of y") → switch to `strict`.

### Recovery procedures

1. **Lost device, has recovery codes:** on the sign-in "Verify it's you" step choose *Lost your device? Use a recovery code*. Then Security → Disable (password + recovery code) and re-enroll, or Regenerate codes.
2. **Lost device and codes:** an administrator opens Admin › Users › *Reset MFA*, re-enters **their own** password, after verifying the user's identity out of band. This deletes the user's MFA and recovery codes, signs out all their sessions and writes `mfa.admin_reset`. Admins cannot reset their own MFA this way.
3. **Encryption key lost or rotated:** stored secrets can no longer be decrypted; users sign in with a recovery code, or an admin resets MFA (procedure 2).

## 5. Session and token lifecycle

| Token | Lifetime | Storage | Notes |
|---|---|---|---|
| Access JWT (HS256) | 15 min | React memory only (never localStorage) | Claims `sub, role, type=access, mfa, jti, iat, exp`. Role re-checked against the DB on every request. |
| Refresh token | 7 days | HttpOnly cookie, `SameSite=Lax`, `Secure` required in production, path `/api/v1/auth` | Opaque random 48 bytes, **SHA-256 hash** stored. Rotated on every refresh. |
| MFA challenge token | 5 min | Login page memory | `type=mfa_challenge`; useless outside `/auth/mfa/verify` |
| Enrollment token | 15 min | Login page memory | `type=mfa_enroll`; only accepted by `/auth/mfa/status` and `/auth/mfa/enroll/*` |

- **Rotation families and reuse detection.** All refresh tokens from one sign-in share a `family_id`. Presenting an already-rotated token after a 15 s grace window revokes the whole family and audits `auth.refresh_reuse_detected` (stolen-token signal). Isolated test `test_refresh_reuse_revokes_family`.
- **Revocation:** logout revokes the presented refresh token; password change and MFA enrollment revoke all *other* sessions; Security page lists active sessions and offers "Sign out other sessions"; admin MFA reset revokes all of the user's sessions.
- **Expiry:** expired refresh tokens are rejected (`test_expired_refresh_rejected`); tampered JWTs are rejected (`test_logout_revokes_and_tampered_token_rejected`).
- **Frontend renewal:** `authFetch` performs one shared refresh for concurrent 401s, retries once, and ends the session cleanly if refresh fails (Vitest `authFetch.test.ts`). Previously the UI broke silently after 15 minutes.
- **CSRF:** data endpoints use Bearer headers (not cookies), so they are not CSRF-able. The cookie is only sent to `/api/v1/auth/*`; `refresh`/`logout` rely on `SameSite=Lax` and an explicit CORS allow-list.
- Tokens, passwords, OTPs, recovery codes and TOTP secrets are never logged (`test_no_secrets_in_logs_or_audit`).

## 6. Authorization (RBAC) matrix

Backend RBAC is authoritative. Employees cannot access another user's tickets, conversations, IT requests, or password-reset records. Agents cannot use admin APIs (models toggle, observability, audit log). Roles in JWT are checked against the database user on every request.

| Capability | Employee | Agent | Admin |
|---|---|---|---|
| Own tickets: create, view, comment | ✅ | — | ✅ (view all) |
| Change ticket status / priority | ❌ 403 | ✅ queue + assigned (working an unassigned ticket claims it) | ✅ |
| Ticket queue, claim | ❌ | ✅ (self only) | ✅ |
| Read other users' conversations | ❌ | ✅ read-only oversight | ✅ read-only |
| Post into someone else's conversation | ❌ | ❌ 403 (fixed this sprint) | ❌ 403 |
| Approve IT requests | ❌ | low/medium risk, not own | ✅ not own |
| Knowledge: read published | ✅ | ✅ | ✅ (+ drafts, write) |
| Users, Audit Log, AI Observability, Ticket Analytics, model toggles, admin MFA reset | ❌ 403 | ❌ 403 | ✅ |
| Own Security settings (MFA, password, sessions) | ✅ | ✅ | ✅ |

Request schemas use `extra="forbid"`: a `role` (or any unknown field) in a payload is rejected with 422 (`test_role_cannot_be_injected_via_payload`). Live test A confirmed employee/agent 403s on admin endpoints against Neon.

## 7. API and application controls

- **Validation:** Pydantic schemas with length limits; 422 responses no longer echo submitted `input` values (previously a password could be reflected back).
- **SQL injection:** SQLAlchemy ORM / bound parameters only.
- **XSS:** React escapes output; no `dangerouslySetInnerHTML` anywhere in `frontend/src`. Security headers middleware sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive `Permissions-Policy`, and HSTS in production. There is no Content-Security-Policy header (limitation).
- **Errors:** unhandled exceptions return `{"detail": "Internal server error"}`; stack traces stay in server logs.
- **CORS:** explicit origin list; `*` rejected in production.
- **IDOR:** ownership checks on tickets, conversations, IT requests, password resets (isolated `test_ticket_and_conversation_idor`; backend audit found no employee IDOR).
- **OpenAPI** `/docs` disabled when `APP_ENV=production`.
- **Uploads:** there are no file-upload endpoints.

## 8. AI / RAG

- LLMs cannot authorize, execute runbooks, or call IAM.
- Retrieved knowledge is labeled as DATA in the generation prompt; citations come only from retrieved chunks.
- Disabled models and unsupported tasks are rejected by `AIModelService`.
- Token counts are provider-reported or null; cost is estimated from configured pricing.
- Retrieved text is untrusted: it cannot change routing or trigger tools. It can still influence wording (live test C echoed an injected topic without acting on it).

## 9. Audit events

Stored in `audit_events` (user, event type, JSON payload, timestamp) and visible in Admin › Audit Log. `GET /api/v1/audits?event_type=mfa.` filters by exact type or by prefix (ending in `.`). Payloads are recursively stripped of keys such as `password`, `token`, `secret`, `otp`.

| Event | When |
|---|---|
| `auth.login`, `auth.login_failed`, `auth.logout`, `auth.refresh` | Sign-in / out / renewal (`auth.login` payload includes `mfa: true/false` and method) |
| `auth.account_locked`, `auth.login_blocked_locked` | Lockout triggered / sign-in attempted while locked |
| `auth.refresh_reuse_detected`, `auth.refresh_rejected_mfa`, `auth.sessions_revoked` | Token theft signal / pre-MFA session refused / sessions revoked (with reason) |
| `auth.password_changed`, `auth.password_change_failed` | Account password change |
| `mfa.challenge_issued`, `mfa.verified`, `mfa.verify_failed`, `mfa.locked` | Second-factor step |
| `mfa.enrollment_started`, `mfa.enrollment_failed`, `mfa.enabled`, `mfa.disabled`, `mfa.disable_failed` | Enrollment lifecycle |
| `mfa.recovery_code_used`, `mfa.recovery_codes_regenerated`, `mfa.admin_reset` | Recovery |
| `authz.denied` | Any 403 (method, path, reason; never the request body) — live test A observed these rows |
| Existing: ticket, chat, IT-request and password-reset workflow events | Unchanged |

User role changes: there is no role-change API in AssistIQ, so there is nothing to audit; roles are assigned by seed scripts.

## 10. Encryption-key configuration

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` (≥ 32 chars) | Signs access / challenge / enrollment JWTs |
| `MFA_ENCRYPTION_KEY` | Fernet key for TOTP secrets and the recovery-code HMAC. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Required in production.** In development/test it is derived from `JWT_SECRET_KEY` (HKDF-SHA256) with a logged warning. |
| `MFA_ENFORCEMENT_MODE`, `MFA_REQUIRED_ROLES`, `MFA_MAX_FAILED_ATTEMPTS`, `MFA_LOCKOUT_MINUTES`, `LOGIN_LOCKOUT_THRESHOLD`, `LOGIN_FAILURE_WINDOW_MINUTES`, `LOGIN_LOCKOUT_MINUTES`, `REFRESH_REUSE_GRACE_SECONDS`, `RATE_LIMIT_MFA_PER_MINUTE` | Policy tuning (defaults in `app/core/config.py`) |

Never commit `backend/.env`. The frontend may only know `VITE_API_BASE_URL`. LLM keys, JWT secrets, encryption keys and database URLs stay on the backend.

## 11. Rate limiting

In-memory sliding windows per client IP, suitable for a **single API process**. Not a distributed limiter. Limits are env-configurable and are not exposed to the frontend.

## 12. Security testing summary

`backend/tests/test_security_mfa.py` (33 tests) + `tests/test_ticket_regressions.py`, run only against the isolated database. Covers: RFC vectors, drift, replay, encryption, recovery-code hashing and single use, enrollment verification, MFA login enforcement and bypass attempts, strict/grace modes, MFA lockout, disable, admin reset, login lockout and generic errors, long passwords, password policy and session revocation, refresh rotation/reuse/expiry/tamper, RBAC matrix with `authz.denied` auditing, role injection, ticket/conversation IDOR, agent posting into others' chats, ticket analytics RBAC, and secrets absent from logs and audit payloads. Results: see `docs/FINAL_SUBMISSION_REPORT.md` §7.
