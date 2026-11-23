import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Query params that must not be forwarded to asyncpg connect().
_UNSAFE_QUERY_PARAMS = frozenset(
    {
        "sslmode",
        "channel_binding",
        "options",
    }
)


def prepare_asyncpg_url(database_url: str) -> tuple[str, dict]:
    """Strip psycopg-style query params and map SSL settings for asyncpg."""
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    connect_args: dict = {}

    sslmode = query.pop("sslmode", [None])[0]
    for key in _UNSAFE_QUERY_PARAMS:
        query.pop(key, None)

    if sslmode in {"require", "verify-ca", "verify-full", "prefer"}:
        connect_args["ssl"] = ssl.create_default_context()
    elif parsed.hostname and parsed.hostname.endswith(".neon.tech"):
        # Neon requires SSL even if sslmode was omitted from a pasted URL.
        connect_args["ssl"] = ssl.create_default_context()

    clean_query = urlencode({key: values[-1] for key, values in query.items() if values})
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, connect_args
