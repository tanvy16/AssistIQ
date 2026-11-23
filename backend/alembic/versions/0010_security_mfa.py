"""Security hardening: TOTP MFA, recovery codes, login throttle, refresh families.

Purely additive: creates three new tables and adds three nullable/defaulted
columns (plus one index) to refresh_tokens. No existing row is modified or removed.

Revision ID: 0010_security_mfa
Revises: 0009_password_reset_workflow
Create Date: 2026-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_security_mfa"
down_revision: Union[str, None] = "0009_password_reset_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_mfa",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("secret_encrypted", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pending_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("pending_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_step", sa.BigInteger(), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])
    op.create_index("ix_mfa_recovery_codes_code_hash", "mfa_recovery_codes", ["code_hash"])
    op.create_table(
        "auth_login_throttle",
        sa.Column("email", sa.String(320), primary_key=True),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("refresh_tokens", sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("refresh_tokens", sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "refresh_tokens",
        sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "mfa_verified")
    op.drop_column("refresh_tokens", "replaced_by_id")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_table("auth_login_throttle")
    op.drop_index("ix_mfa_recovery_codes_code_hash", table_name="mfa_recovery_codes")
    op.drop_index("ix_mfa_recovery_codes_user_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("user_mfa")
