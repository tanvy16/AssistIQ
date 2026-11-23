"""Password reset workflow tables.

Revision ID: 0009_password_reset_workflow
Revises: 0008_it_request_workflow
Create Date: 2026-08-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_password_reset_workflow"
down_revision: Union[str, None] = "0008_it_request_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

password_reset_status = postgresql.ENUM(
    "submitted",
    "verification_required",
    "verification_failed",
    "risk_review",
    "confirmation_required",
    "approved",
    "executing",
    "completed",
    "rejected",
    "escalated",
    "failed",
    name="password_reset_status",
    create_type=False,
)
password_verification_status = postgresql.ENUM(
    "pending",
    "verified",
    "failed",
    "requires_escalation",
    name="password_verification_status",
    create_type=False,
)
password_risk_level = postgresql.ENUM(
    "low", "medium", "high", "critical", name="password_risk_level", create_type=False
)
password_policy_decision = postgresql.ENUM(
    "allow",
    "requires_confirmation",
    "requires_escalation",
    "deny",
    name="password_policy_decision",
    create_type=False,
)


def upgrade() -> None:
    password_reset_status.create(op.get_bind(), checkfirst=True)
    password_verification_status.create(op.get_bind(), checkfirst=True)
    password_risk_level.create(op.get_bind(), checkfirst=True)
    password_policy_decision.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "password_reset_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", password_reset_status, nullable=False),
        sa.Column("verification_status", password_verification_status, nullable=False),
        sa.Column("risk_level", password_risk_level, nullable=False),
        sa.Column("policy_decision", password_policy_decision, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.Column("failed_verification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("adapter_name", sa.String(length=64), nullable=True),
        sa.Column("execution_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["escalation_id"], ["escalations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_requests_requester_id", "password_reset_requests", ["requester_id"])
    op.create_index("ix_password_reset_requests_target_user_id", "password_reset_requests", ["target_user_id"])
    op.create_index("ix_password_reset_requests_status", "password_reset_requests", ["status"])

    op.create_table(
        "password_reset_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["password_reset_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_events_request_id", "password_reset_events", ["request_id"])
    op.create_index("ix_password_reset_events_event_type", "password_reset_events", ["event_type"])

    op.create_table(
        "password_reset_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_stage", sa.String(length=64), nullable=False),
        sa.Column("verification_result", sa.String(length=32), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("policy_decision", sa.String(length=32), nullable=True),
        sa.Column("execution_result", sa.String(length=32), nullable=True),
        sa.Column("verification_latency_ms", sa.Float(), nullable=True),
        sa.Column("policy_latency_ms", sa.Float(), nullable=True),
        sa.Column("iam_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_workflow_latency_ms", sa.Float(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["password_reset_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_telemetry_request_id", "password_reset_telemetry", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_telemetry_request_id", table_name="password_reset_telemetry")
    op.drop_table("password_reset_telemetry")
    op.drop_index("ix_password_reset_events_event_type", table_name="password_reset_events")
    op.drop_index("ix_password_reset_events_request_id", table_name="password_reset_events")
    op.drop_table("password_reset_events")
    op.drop_index("ix_password_reset_requests_status", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_target_user_id", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_requester_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")
    password_policy_decision.drop(op.get_bind(), checkfirst=True)
    password_risk_level.drop(op.get_bind(), checkfirst=True)
    password_verification_status.drop(op.get_bind(), checkfirst=True)
    password_reset_status.drop(op.get_bind(), checkfirst=True)
