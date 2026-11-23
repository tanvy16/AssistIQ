from app.core.db_errors import classify_database_error, sanitize_error_message
from app.core.db_url import prepare_asyncpg_url


def test_prepare_asyncpg_url_strips_sslmode_and_channel_binding():
    raw = (
        "postgresql+asyncpg://user:pass@ep-example.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    url, connect_args = prepare_asyncpg_url(raw)

    assert "sslmode=" not in url
    assert "channel_binding=" not in url
    assert "ssl" in connect_args


def test_classify_dns_error():
    exc = OSError("[Errno 11001] getaddrinfo failed")
    assert classify_database_error(exc) == "dns_resolution_failed"


def test_sanitize_error_message_redacts_credentials():
    message = "connection to postgresql+asyncpg://user:secret@host/db failed"
    sanitized = sanitize_error_message(message)
    assert "secret" not in sanitized
    assert "[REDACTED]" in sanitized
