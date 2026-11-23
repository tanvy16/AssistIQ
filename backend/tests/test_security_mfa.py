"""Security tests: TOTP MFA, recovery codes, lockout, token rotation, RBAC, IDOR.

DB-backed tests run only against the disposable loopback database
(backend/scripts/run_isolated_tests.ps1); conftest skips them otherwise.
Pure unit tests at the top run anywhere.
"""

import logging
import time

import pytest
from sqlalchemy import select

from app.core import mfa as mfa_core
from app.core.config import get_settings
from app.core.mfa import (
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    hotp,
    match_totp_step,
    totp_at,
)
from tests.conftest import ticket_payload

RFC_SECRET_B32 = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # b"12345678901234567890"


# ------------------------------------------------------------------ unit


@pytest.mark.parametrize(
    ("unix_time", "expected"),
    [(59, "94287082"), (1111111109, "07081804"), (1234567890, "89005924"), (2000000000, "69279037")],
)
def test_totp_matches_rfc6238_sha1_vectors(unix_time, expected):
    assert totp_at(RFC_SECRET_B32, unix_time, digits=8) == expected


def test_hotp_matches_rfc4226_vectors():
    key = b"12345678901234567890"
    expected = ["755224", "287082", "359152", "969429", "338314"]
    assert [hotp(key, i) for i in range(5)] == expected


def test_totp_accepts_one_step_drift_and_rejects_two():
    secret = generate_totp_secret()
    now = 1_700_000_000
    assert match_totp_step(secret, totp_at(secret, now - 30), now=now) is not None
    assert match_totp_step(secret, totp_at(secret, now + 30), now=now) is not None
    assert match_totp_step(secret, totp_at(secret, now - 90), now=now) is None
    assert match_totp_step(secret, "12345", now=now) is None
    assert match_totp_step(secret, "abcdef", now=now) is None


def test_totp_replay_rejected_by_last_used_step():
    secret = generate_totp_secret()
    now = 1_700_000_000
    code = totp_at(secret, now)
    step = match_totp_step(secret, code, now=now)
    assert step is not None
    assert match_totp_step(secret, code, now=now, last_used_step=step) is None


def test_secret_encryption_roundtrip_and_ciphertext_hides_secret():
    secret = generate_totp_secret()
    token = encrypt_secret(secret)
    assert secret not in token
    assert decrypt_secret(token) == secret


def test_secret_cannot_be_decrypted_with_another_key(monkeypatch):
    secret = generate_totp_secret()
    token = encrypt_secret(secret)
    from cryptography.fernet import Fernet

    monkeypatch.setenv("MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    mfa_core.reset_mfa_crypto_cache()
    try:
        with pytest.raises(mfa_core.MFASecretError):
            decrypt_secret(token)
    finally:
        monkeypatch.delenv("MFA_ENCRYPTION_KEY")
        get_settings.cache_clear()
        mfa_core.reset_mfa_crypto_cache()


def test_recovery_codes_are_unique_and_hash_normalised():
    codes = generate_recovery_codes(10)
    assert len(set(codes)) == 10
    code = codes[0]
    assert hash_recovery_code(code) == hash_recovery_code(code.lower().replace("-", " "))
    assert code not in hash_recovery_code(code)


def test_production_requires_mfa_encryption_key():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://u:p@h/db?sslmode=require",
            JWT_SECRET_KEY="x" * 40,
            COOKIE_SECURE=True,
            CORS_ORIGINS=["https://app.example.com"],
        )


def test_loopback_database_without_ssl_only_allowed_in_test_env():
    from pydantic import ValidationError

    from app.core.config import Settings

    url = "postgresql+asyncpg://u:p@127.0.0.1:5432/db"
    Settings(APP_ENV="test", DATABASE_URL=url, JWT_SECRET_KEY="x" * 40)
    with pytest.raises(ValidationError):
        Settings(APP_ENV="development", DATABASE_URL=url, JWT_SECRET_KEY="x" * 40)
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="test",
            DATABASE_URL="postgresql+asyncpg://u:p@shared.example.com/db",
            JWT_SECRET_KEY="x" * 40,
        )


def test_password_policy():
    from app.services.auth_service import PasswordPolicyError, validate_new_password

    validate_new_password("Correct-Horse-42", email="pat@example.com")
    for weak in ["short1A!", "alllowercaseletters", "patrick-Secure-99"]:
        with pytest.raises(PasswordPolicyError):
            validate_new_password(weak, email="patrick@example.com")
    with pytest.raises(PasswordPolicyError):
        validate_new_password("Same-Password-1", email="a@b.co", current_password="Same-Password-1")


# ------------------------------------------------------------------ HTTP helpers


class Clock:
    def __init__(self) -> None:
        self.now = float(int(time.time()) // 30 * 30 + 1)

    def advance(self, seconds: int = 30) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(mfa_core.time, "time", c)
    return c


@pytest.fixture(autouse=True)
def generous_mfa_rate_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MFA_PER_MINUTE", "500")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_MINUTE", "500")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_env(monkeypatch, **values):
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


async def _password_login(client, email, password):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def _enroll(client, token, password, clock):
    start = await client.post(
        "/api/v1/auth/mfa/enroll/start", headers=_bearer(token), json={"password": password}
    )
    assert start.status_code == 200, start.text
    secret = start.json()["secret"]
    clock.advance()
    verify = await client.post(
        "/api/v1/auth/mfa/enroll/verify",
        headers=_bearer(token),
        json={"code": totp_at(secret, clock())},
    )
    assert verify.status_code == 200, verify.text
    return secret, verify.json()


# ------------------------------------------------------------------ enrollment


@pytest.mark.asyncio
async def test_enrollment_requires_password_and_first_code(client, employee_user, clock):
    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    token = login.json()["access_token"]
    assert login.json()["user"]["mfa_enabled"] is False

    bad = await client.post(
        "/api/v1/auth/mfa/enroll/start", headers=_bearer(token), json={"password": "wrong-password"}
    )
    assert bad.status_code == 403

    start = await client.post(
        "/api/v1/auth/mfa/enroll/start", headers=_bearer(token), json={"password": "EmployeePass123!"}
    )
    assert start.status_code == 200
    body = start.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["qr_svg_data_uri"].startswith("data:image/svg+xml")
    secret = body["secret"]

    status_resp = await client.get("/api/v1/auth/mfa/status", headers=_bearer(token))
    assert status_resp.json()["enabled"] is False  # not enabled before verification
    assert status_resp.json()["pending_enrollment"] is True
    assert secret not in status_resp.text

    wrong = await client.post(
        "/api/v1/auth/mfa/enroll/verify", headers=_bearer(token), json={"code": "000000"}
    )
    assert wrong.status_code == 400
    assert (await client.get("/api/v1/auth/mfa/status", headers=_bearer(token))).json()["enabled"] is False

    clock.advance()
    ok = await client.post(
        "/api/v1/auth/mfa/enroll/verify",
        headers=_bearer(token),
        json={"code": totp_at(secret, clock())},
    )
    assert ok.status_code == 200
    codes = ok.json()["recovery_codes"]
    assert len(codes) == 10

    new_token = ok.json()["access_token"]
    status_after = await client.get("/api/v1/auth/mfa/status", headers=_bearer(new_token))
    data = status_after.json()
    assert data["enabled"] is True and data["recovery_codes_remaining"] == 10
    assert secret not in status_after.text
    assert all(code not in status_after.text for code in codes)


@pytest.mark.asyncio
async def test_secret_stored_encrypted_and_codes_hashed(client, employee_user, db_session, clock):
    from app.models.security import MFARecoveryCode, UserMFA

    token = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["access_token"]
    secret, result = await _enroll(client, token, "EmployeePass123!", clock)
    record = await db_session.get(UserMFA, employee_user.id)
    assert record.enabled is True
    assert secret not in (record.secret_encrypted or "")
    rows = (await db_session.execute(select(MFARecoveryCode).where(MFARecoveryCode.user_id == employee_user.id))).scalars().all()
    stored = {row.code_hash for row in rows}
    assert all(code not in stored for code in result["recovery_codes"])
    assert len(stored) == 10


# ------------------------------------------------------------------ login enforcement


@pytest.mark.asyncio
async def test_enrolled_user_cannot_bypass_mfa(client, employee_user, clock):
    other_device = await _password_login(client, employee_user.email, "EmployeePass123!")
    other_refresh = other_device.cookies.get("assistiq_refresh")
    client.cookies.clear()
    first = await _password_login(client, employee_user.email, "EmployeePass123!")
    pre_token = first.json()["access_token"]
    secret, enroll = await _enroll(client, pre_token, "EmployeePass123!", clock)

    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is True
    assert body["access_token"] is None
    assert "assistiq_refresh" not in login.cookies
    challenge = body["mfa_token"]

    # The challenge token is not an access token.
    assert (await client.get("/api/v1/tickets", headers=_bearer(challenge))).status_code == 401

    # A token minted before enrollment (no mfa claim) is no longer accepted.
    client.cookies.clear()
    stale = await client.get("/api/v1/tickets", headers=_bearer(pre_token))
    assert stale.status_code == 401

    # Wrong code -> 400, nothing issued.
    bad = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": "123456"})
    assert bad.status_code == 400

    clock.advance()
    code = totp_at(secret, clock())
    good = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": code})
    assert good.status_code == 200
    token = good.json()["access_token"]
    assert (await client.get("/api/v1/tickets", headers=_bearer(token))).status_code == 200

    # Replay of the same code is rejected.
    replay = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": code})
    assert replay.status_code == 400

    # Sessions on other devices were revoked when MFA was enabled; they cannot
    # be renewed into the now MFA-protected account.
    client.cookies.clear()
    old_refresh = await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": other_refresh})
    assert old_refresh.status_code == 401


@pytest.mark.asyncio
async def test_recovery_code_works_exactly_once(client, employee_user, clock):
    token = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["access_token"]
    _secret, enroll = await _enroll(client, token, "EmployeePass123!", clock)
    recovery = enroll["recovery_codes"][0]

    challenge = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["mfa_token"]
    used = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "recovery_code": recovery})
    assert used.status_code == 200
    status_resp = await client.get("/api/v1/auth/mfa/status", headers=_bearer(used.json()["access_token"]))
    assert status_resp.json()["recovery_codes_remaining"] == 9

    challenge2 = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["mfa_token"]
    again = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge2, "recovery_code": recovery})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_mfa_lockout_after_repeated_wrong_codes(client, employee_user, clock):
    token = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["access_token"]
    secret, _ = await _enroll(client, token, "EmployeePass123!", clock)
    challenge = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["mfa_token"]
    for _ in range(5):
        r = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": "000000"})
        assert r.status_code == 400
    clock.advance()
    locked = await client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": totp_at(secret, clock())}
    )
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers


@pytest.mark.asyncio
async def test_disable_mfa_requires_password_and_code(client, employee_user, clock):
    token = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["access_token"]
    secret, enroll = await _enroll(client, token, "EmployeePass123!", clock)
    token = enroll["access_token"]
    clock.advance()
    wrong_pw = await client.post(
        "/api/v1/auth/mfa/disable",
        headers=_bearer(token),
        json={"password": "nope-nope", "code": totp_at(secret, clock())},
    )
    assert wrong_pw.status_code == 403
    clock.advance()
    ok = await client.post(
        "/api/v1/auth/mfa/disable",
        headers=_bearer(token),
        json={"password": "EmployeePass123!", "code": totp_at(secret, clock())},
    )
    assert ok.status_code == 200
    relog = await _password_login(client, employee_user.email, "EmployeePass123!")
    assert relog.json()["mfa_required"] is False and relog.json()["access_token"]


@pytest.mark.asyncio
async def test_strict_mode_requires_agent_enrollment_before_any_access(client, agent_user, clock, monkeypatch):
    _set_env(monkeypatch, MFA_ENFORCEMENT_MODE="strict")
    login = await _password_login(client, agent_user.email, "AgentPass123!")
    body = login.json()
    assert body["access_token"] is None
    assert body["mfa_enrollment_required"] is True
    enroll_token = body["enrollment_token"]
    assert "assistiq_refresh" not in login.cookies

    # Enrollment token cannot be used against application APIs.
    assert (await client.get("/api/v1/tickets", headers=_bearer(enroll_token))).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers=_bearer(enroll_token))).status_code == 401

    secret, result = await _enroll(client, enroll_token, "AgentPass123!", clock)
    assert result["access_token"]
    assert (await client.get("/api/v1/tickets?scope=queue", headers=_bearer(result["access_token"]))).status_code == 200

    # Mandatory role: cannot disable in strict mode.
    clock.advance()
    blocked = await client.post(
        "/api/v1/auth/mfa/disable",
        headers=_bearer(result["access_token"]),
        json={"password": "AgentPass123!", "code": totp_at(secret, clock())},
    )
    assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_grace_mode_flags_privileged_enrollment_without_lockout(client, admin_user, monkeypatch):
    _set_env(monkeypatch, MFA_ENFORCEMENT_MODE="grace")
    login = await _password_login(client, admin_user.email, "AdminPass123!")
    body = login.json()
    assert body["access_token"]
    assert body["mfa_enrollment_required"] is True
    me = await client.get("/api/v1/auth/me", headers=_bearer(body["access_token"]))
    assert me.json()["mfa_enrollment_required"] is True


# ------------------------------------------------------------------ password / lockout


@pytest.mark.asyncio
async def test_login_lockout_and_generic_errors(client, employee_user, db_session):
    from app.models.audit_event import AuditEvent

    unknown = await _password_login(client, "nobody-xyz@example.com", "WrongPass123!")
    wrong = await _password_login(client, employee_user.email, "WrongPass123!")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()

    for _ in range(4):
        await _password_login(client, employee_user.email, "WrongPass123!")
    locked = await _password_login(client, employee_user.email, "EmployeePass123!")
    assert locked.status_code == 429
    assert "access_token" not in locked.json()

    events = (
        await db_session.execute(
            select(AuditEvent.event_type).where(AuditEvent.payload["email"].astext == employee_user.email)
        )
    ).scalars().all()
    assert "auth.account_locked" in events and "auth.login_failed" in events


@pytest.mark.asyncio
async def test_long_password_does_not_500(client, employee_user):
    r = await _password_login(client, employee_user.email, "A" * 120)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_password_change_validates_and_revokes_other_sessions(client, employee_user):
    a = await _password_login(client, employee_user.email, "EmployeePass123!")
    other_refresh = a.cookies.get("assistiq_refresh")
    client.cookies.clear()
    b = await _password_login(client, employee_user.email, "EmployeePass123!")
    token = b.json()["access_token"]

    weak = await client.post(
        "/api/v1/auth/password/change",
        headers=_bearer(token),
        json={"current_password": "EmployeePass123!", "new_password": "short"},
    )
    assert weak.status_code == 422
    wrong = await client.post(
        "/api/v1/auth/password/change",
        headers=_bearer(token),
        json={"current_password": "bad-current", "new_password": "Brand-New-Pass-77"},
    )
    assert wrong.status_code == 403
    ok = await client.post(
        "/api/v1/auth/password/change",
        headers=_bearer(token),
        json={"current_password": "EmployeePass123!", "new_password": "Brand-New-Pass-77"},
    )
    assert ok.status_code == 200 and ok.json()["revoked"] >= 1
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": other_refresh})).status_code == 401
    assert (await _password_login(client, employee_user.email, "Brand-New-Pass-77")).status_code == 200


# ------------------------------------------------------------------ tokens


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family(client, employee_user, monkeypatch):
    _set_env(monkeypatch, REFRESH_REUSE_GRACE_SECONDS="0")
    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    r0 = login.cookies.get("assistiq_refresh")
    client.cookies.clear()
    first = await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": r0})
    assert first.status_code == 200
    r1 = first.cookies.get("assistiq_refresh")
    client.cookies.clear()
    # Attacker replays the rotated token -> rejected, and the family is revoked.
    reuse = await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": r0})
    assert reuse.status_code == 401
    client.cookies.clear()
    legit = await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": r1})
    assert legit.status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_rejected(client, employee_user, db_session):
    from datetime import UTC, datetime, timedelta

    from app.core.security import hash_refresh_token
    from app.models.refresh_token import RefreshToken

    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    raw = login.cookies.get("assistiq_refresh")
    record = await db_session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": raw})).status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_and_tampered_token_rejected(client, employee_user):
    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    raw = login.cookies.get("assistiq_refresh")
    token = login.json()["access_token"]
    await client.post("/api/v1/auth/logout", cookies={"assistiq_refresh": raw})
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", cookies={"assistiq_refresh": raw})).status_code == 401
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert (await client.get("/api/v1/auth/me", headers=_bearer(tampered))).status_code == 401


# ------------------------------------------------------------------ RBAC / IDOR


@pytest.mark.asyncio
async def test_rbac_matrix_and_denials_audited(client, employee_auth, agent_auth, admin_auth, employee_user, db_session):
    from app.models.audit_event import AuditEvent

    for path in ["/api/v1/audits", "/api/v1/users", "/api/v1/observability/cost"]:
        assert (await client.get(path, headers=employee_auth)).status_code == 403
    for path in ["/api/v1/audits", "/api/v1/users", "/api/v1/observability/cost"]:
        assert (await client.get(path, headers=agent_auth)).status_code == 403
    for path in ["/api/v1/audits", "/api/v1/users"]:
        assert (await client.get(path, headers=admin_auth)).status_code == 200

    denied = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "authz.denied", AuditEvent.user_id == employee_user.id
            )
        )
    ).scalars().all()
    assert {e.payload["path"] for e in denied} >= {"/api/v1/audits", "/api/v1/users"}


@pytest.mark.asyncio
async def test_role_cannot_be_injected_via_payload(client, employee_user):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": employee_user.email, "password": "EmployeePass123!", "role": "admin"},
    )
    assert r.status_code == 422
    assert "EmployeePass123!" not in r.text  # 422 never echoes submitted values


@pytest.mark.asyncio
async def test_ticket_and_conversation_idor(
    client, ai_models, employee_auth, employee_b_auth, agent_auth, sla_policies
):
    created = await client.post("/api/v1/tickets", headers=employee_auth, json=ticket_payload())
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert (await client.get(f"/api/v1/tickets/{ticket_id}", headers=employee_b_auth)).status_code in (403, 404)
    assert (
        await client.patch(f"/api/v1/tickets/{ticket_id}", headers=employee_auth, json={"status": "resolved"})
    ).status_code == 403

    conv = await client.post("/api/v1/chat/conversations", headers=employee_auth, json={"title": "private"})
    assert conv.status_code == 201
    conv_id = conv.json()["id"]
    assert (await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=employee_b_auth)).status_code in (403, 404)
    # Agents may read for oversight but cannot post into someone else's chat.
    post = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages", headers=agent_auth, json={"content": "hi"}
    )
    assert post.status_code == 403


@pytest.mark.asyncio
async def test_admin_mfa_reset_recovery_path(client, employee_user, admin_auth, admin_user, clock):
    token = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["access_token"]
    await _enroll(client, token, "EmployeePass123!", clock)
    wrong = await client.post(
        f"/api/v1/users/{employee_user.id}/mfa/reset", headers=admin_auth, json={"admin_password": "nope"}
    )
    assert wrong.status_code == 403
    ok = await client.post(
        f"/api/v1/users/{employee_user.id}/mfa/reset", headers=admin_auth, json={"admin_password": "AdminPass123!"}
    )
    assert ok.status_code == 200
    relog = await _password_login(client, employee_user.email, "EmployeePass123!")
    assert relog.json()["mfa_required"] is False
    self_reset = await client.post(
        f"/api/v1/users/{admin_user.id}/mfa/reset", headers=admin_auth, json={"admin_password": "AdminPass123!"}
    )
    assert self_reset.status_code == 409


@pytest.mark.asyncio
async def test_no_secrets_in_logs_or_audit(client, employee_user, db_session, clock, caplog):
    from app.models.audit_event import AuditEvent

    caplog.set_level(logging.DEBUG)
    login = await _password_login(client, employee_user.email, "EmployeePass123!")
    token = login.json()["access_token"]
    secret, enroll = await _enroll(client, token, "EmployeePass123!", clock)
    challenge = (await _password_login(client, employee_user.email, "EmployeePass123!")).json()["mfa_token"]
    clock.advance()
    code = totp_at(secret, clock())
    await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": code})

    sensitive = [secret, code, "EmployeePass123!", token, *enroll["recovery_codes"]]
    log_text = caplog.text
    assert all(value not in log_text for value in sensitive)
    payloads = (
        await db_session.execute(select(AuditEvent.payload).where(AuditEvent.user_id == employee_user.id))
    ).scalars().all()
    audit_text = repr(payloads)
    assert all(value not in audit_text for value in sensitive)


@pytest.mark.asyncio
async def test_ticket_analytics_is_admin_only_and_real(client, employee_auth, agent_auth, admin_auth, sla_policies):
    assert (await client.get("/api/v1/analytics/tickets", headers=employee_auth)).status_code == 403
    assert (await client.get("/api/v1/analytics/tickets", headers=agent_auth)).status_code == 403
    assert (await client.get("/api/v1/analytics/tickets?days=5", headers=admin_auth)).status_code == 422
    before = (await client.get("/api/v1/analytics/tickets?days=7", headers=admin_auth)).json()
    assert len(before["daily"]) == 7
    created = await client.post("/api/v1/tickets", headers=employee_auth, json=ticket_payload(priority="high"))
    assert created.status_code == 201
    after = (await client.get("/api/v1/analytics/tickets?days=7", headers=admin_auth)).json()
    assert after["totals"]["created"] == before["totals"]["created"] + 1
    assert after["daily"][-1]["created"] == before["daily"][-1]["created"] + 1
    assert after["status"]["open"] == before["status"]["open"] + 1
    assert after["active_by_priority"]["high"] == before["active_by_priority"]["high"] + 1
    assert after["has_data"] is True
