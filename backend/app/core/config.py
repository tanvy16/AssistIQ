from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def is_loopback_database_url(database_url: str) -> bool:
    from urllib.parse import urlparse

    try:
        host = urlparse(database_url).hostname
    except ValueError:
        return False
    return bool(host) and host in LOOPBACK_HOSTS


class Settings(BaseSettings):
    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://127.0.0.1:5173"]

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_COOKIE_NAME: str = "assistiq_refresh"
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    TRUST_FORWARDED_FOR: bool = False

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 30
    RATE_LIMIT_REFRESH_PER_MINUTE: int = 60
    RATE_LIMIT_AI_PER_MINUTE: int = 30
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    RATE_LIMIT_SEARCH_PER_MINUTE: int = 40
    RATE_LIMIT_IT_PER_MINUTE: int = 20
    RATE_LIMIT_PASSWORD_RESET_PER_MINUTE: int = 15
    RATE_LIMIT_MFA_PER_MINUTE: int = 10

    # Account protection (failed-login lockout, keyed by normalised email so it
    # behaves identically for unknown emails and never reveals which exist).
    LOGIN_LOCKOUT_THRESHOLD: int = 5
    LOGIN_FAILURE_WINDOW_MINUTES: int = 15
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Multi-factor authentication (TOTP, RFC 6238).
    # MFA_ENCRYPTION_KEY: Fernet key (urlsafe base64, 32 bytes) used to encrypt
    # stored TOTP secrets. Required in production. In development/test only, a
    # key is derived from JWT_SECRET_KEY via HKDF when unset (a warning is logged).
    MFA_ENCRYPTION_KEY: str | None = None
    MFA_ISSUER: str = "AssistIQ"
    MFA_REQUIRED_ROLES: list[str] = ["admin", "agent"]
    # strict: users in MFA_REQUIRED_ROLES get no access token until enrolled.
    # grace: they are signed in but flagged mfa_enrollment_required (UI prompt).
    # Unset -> strict in production, grace otherwise (protects seeded demo
    # accounts from an unexpected lockout).
    MFA_ENFORCEMENT_MODE: Literal["strict", "grace"] | None = None
    MFA_CHALLENGE_TOKEN_MINUTES: int = 5
    MFA_MAX_FAILED_ATTEMPTS: int = 5
    MFA_LOCKOUT_MINUTES: int = 15
    MFA_RECOVERY_CODE_COUNT: int = 10
    # A rotated refresh token presented again after this grace period is treated
    # as theft: the whole token family is revoked.
    REFRESH_REUSE_GRACE_SECONDS: int = 15

    # RAG / Chroma (Phase 4)
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "kb_chunks"
    EMBEDDING_MODEL_ID: str = "hash-v1"
    EMBEDDING_DIMENSION: int = 384
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_SEARCH_TOP_K_MAX: int = 20

    # AI / LLM (Phase 5)
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_DEFAULT_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 180.0
    LLM_MAX_TOKENS: int = 400
    # Startup keep-alive prompt to a local Ollama model. It is a real (tiny)
    # generation, so it can be disabled when generations must be counted.
    LLM_PREWARM_ENABLED: bool = True

    # Chat / RAG (Phase 6)
    CHAT_HISTORY_LIMIT: int = 6
    CHAT_RETRIEVAL_TOP_K: int = 3
    CHAT_CONFIDENCE_HIGH_THRESHOLD: float = 0.65
    CHAT_CONFIDENCE_LOW_THRESHOLD: float = 0.35

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value or value.startswith("postgresql+asyncpg://USER:"):
            raise ValueError(
                "DATABASE_URL must be set to a valid Neon connection string in backend/.env"
            )
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg:// driver")
        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value or len(value.strip()) < 32:
            raise ValueError("JWT_SECRET_KEY must be set and at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_database_ssl(self) -> Self:
        # Neon (and any shared database) must use TLS. The only exception is a
        # disposable loopback database used for isolated tests (APP_ENV=test).
        if "sslmode=require" in self.DATABASE_URL:
            return self
        if self.APP_ENV == "test" and is_loopback_database_url(self.DATABASE_URL):
            return self
        raise ValueError("DATABASE_URL must include sslmode=require for Neon")

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        if self.APP_ENV == "production":
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true when APP_ENV=production")
            if any(origin.strip() == "*" for origin in self.CORS_ORIGINS):
                raise ValueError("CORS_ORIGINS cannot include * in production")
            if not self.MFA_ENCRYPTION_KEY:
                raise ValueError("MFA_ENCRYPTION_KEY must be set when APP_ENV=production")
        return self

    @property
    def mfa_enforcement_mode(self) -> str:
        if self.MFA_ENFORCEMENT_MODE:
            return self.MFA_ENFORCEMENT_MODE
        return "strict" if self.is_production else "grace"

    def role_requires_mfa(self, role: str) -> bool:
        return role in {item.strip().lower() for item in self.MFA_REQUIRED_ROLES}

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def llm_pricing_for(self, model_name: str) -> tuple[float, float] | None:
        """Return (input_usd_per_1k, output_usd_per_1k) when known."""
        pricing: dict[str, tuple[float, float]] = {
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4o": (0.0025, 0.01),
        }
        return pricing.get(model_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
