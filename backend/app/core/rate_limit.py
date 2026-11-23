"""In-memory sliding-window rate limiter for single-instance deployments."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

BUCKET_LIMITS = {
    "login": ("RATE_LIMIT_LOGIN_PER_MINUTE", 30),
    "refresh": ("RATE_LIMIT_REFRESH_PER_MINUTE", 60),
    "ai": ("RATE_LIMIT_AI_PER_MINUTE", 30),
    "chat": ("RATE_LIMIT_CHAT_PER_MINUTE", 30),
    "search": ("RATE_LIMIT_SEARCH_PER_MINUTE", 40),
    "it": ("RATE_LIMIT_IT_PER_MINUTE", 20),
    "password_reset": ("RATE_LIMIT_PASSWORD_RESET_PER_MINUTE", 15),
    "mfa": ("RATE_LIMIT_MFA_PER_MINUTE", 10),
}


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            retry_after = int(window[0] + window_seconds - now) + 1
            return False, max(retry_after, 1)
        window.append(now)
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    return _limiter


def reset_rate_limiter() -> None:
    _limiter.reset()


def client_key(request: Request) -> str:
    settings = get_settings()
    if settings.TRUST_FORWARDED_FOR:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit(bucket: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return
        attr, default = BUCKET_LIMITS[bucket]
        limit = int(getattr(settings, attr, default))
        allowed, retry_after = _limiter.allow(f"{bucket}:{client_key(request)}", limit)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
