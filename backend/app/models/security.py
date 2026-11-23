"""MFA and account-protection tables (migration 0010_security_mfa).

Kept separate from ``users`` so the change is purely additive: no existing
column is altered and seeded accounts keep working unchanged.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserMFA(Base):
    __tablename__ = "user_mfa"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Fernet ciphertext of the base32 TOTP secret. Never returned by the API
    # after enrollment and never logged.
    secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Enrollment in progress: the secret is not active until the first code verifies.
    pending_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Highest TOTP time-step accepted so far; codes at or below it are replays.
    last_used_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class MFARecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # HMAC-SHA256 of the normalised code, keyed with a server secret. The raw
    # code is shown to the user exactly once and never stored.
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LoginThrottle(Base):
    """Failed-login counter per normalised email (also exists for unknown emails)."""

    __tablename__ = "auth_login_throttle"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
