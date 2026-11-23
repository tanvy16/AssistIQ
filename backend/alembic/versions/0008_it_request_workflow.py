"""IT request workflow tables, catalogs, and runbooks.

Revision ID: 0008_it_request_workflow
Revises: 0007_chat_and_rag_conversations
Create Date: 2026-08-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_it_request_workflow"
down_revision: Union[str, None] = "0007_chat_and_rag_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

it_request_type = postgresql.ENUM("software", "access", "permission", name="it_request_type", create_type=False)
it_request_status = postgresql.ENUM(
    "submitted",
    "parsed",
    "policy_review",
    "approval_required",
    "approved",
    "rejected",
    "planned",
    "executing",
    "validating",
    "completed",
    "failed",
    "rolled_back",
    "escalated",
    "cancelled",
    name="it_request_status",
    create_type=False,
)
it_risk_level = postgresql.ENUM("low", "medium", "high", "critical", name="it_risk_level", create_type=False)
it_approval_status = postgresql.ENUM(
    "pending", "approved", "rejected", "cancelled", name="it_approval_status", create_type=False
)
it_execution_status = postgresql.ENUM(
    "pending", "running", "success", "failed", "rolled_back", name="it_execution_status", create_type=False
)
it_policy_decision = postgresql.ENUM(
    "allow", "deny", "approval_required", "escalate", name="it_policy_decision", create_type=False
)


def upgrade() -> None:
    it_request_type.create(op.get_bind(), checkfirst=True)
    it_request_status.create(op.get_bind(), checkfirst=True)
    it_risk_level.create(op.get_bind(), checkfirst=True)
    it_approval_status.create(op.get_bind(), checkfirst=True)
    it_execution_status.create(op.get_bind(), checkfirst=True)
    it_policy_decision.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "runbooks",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("risk_level", it_risk_level, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rollback_supported", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "software_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("vendor", sa.String(length=128), nullable=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("package_identifier", sa.String(length=128), nullable=False),
        sa.Column("risk_level", it_risk_level, nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("runbook_id", sa.String(length=128), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["runbook_id"], ["runbooks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("package_identifier"),
    )

    op.create_table(
        "access_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_name", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="corporate"),
        sa.Column("risk_level", it_risk_level, nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("runbook_id", sa.String(length=128), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["runbook_id"], ["runbooks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_name"),
    )

    op.create_table(
        "it_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", it_request_type, nullable=False),
        sa.Column("status", it_request_status, nullable=False),
        sa.Column("requested_resource", sa.String(length=255), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("risk_level", it_risk_level, nullable=False),
        sa.Column("policy_decision", it_policy_decision, nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("selected_runbook_id", sa.String(length=128), nullable=True),
        sa.Column("catalog_kind", sa.String(length=32), nullable=True),
        sa.Column("catalog_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_runbook_id"], ["runbooks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_it_requests_requester_id", "it_requests", ["requester_id"])
    op.create_index("ix_it_requests_status", "it_requests", ["status"])

    op.create_table(
        "request_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_name", sa.String(length=128), nullable=False),
        sa.Column("entity_value", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="deterministic"),
        sa.ForeignKeyConstraint(["request_id"], ["it_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_entities_request_id", "request_entities", ["request_id"])

    op.create_table(
        "request_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", it_approval_status, nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["it_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_approvals_request_id", "request_approvals", ["request_id"])

    op.create_table(
        "runbook_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runbook_id", sa.String(length=128), nullable=False),
        sa.Column("status", it_execution_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rollback_status", sa.String(length=32), nullable=True),
        sa.Column("adapter_name", sa.String(length=64), nullable=False, server_default="mock"),
        sa.ForeignKeyConstraint(["request_id"], ["it_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["runbook_id"], ["runbooks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runbook_executions_request_id", "runbook_executions", ["request_id"])

    op.create_table(
        "request_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["it_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_events_request_id", "request_events", ["request_id"])
    op.create_index("ix_request_events_event_type", "request_events", ["event_type"])

    op.create_table(
        "it_workflow_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_latency_ms", sa.Float(), nullable=True),
        sa.Column("policy_latency_ms", sa.Float(), nullable=True),
        sa.Column("planning_latency_ms", sa.Float(), nullable=True),
        sa.Column("execution_latency_ms", sa.Float(), nullable=True),
        sa.Column("validation_latency_ms", sa.Float(), nullable=True),
        sa.Column("rollback_latency_ms", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("policy_decision", sa.String(length=32), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("execution_status", sa.String(length=32), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=True),
        sa.Column("rollback_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["it_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_it_workflow_telemetry_request_id", "it_workflow_telemetry", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_it_workflow_telemetry_request_id", table_name="it_workflow_telemetry")
    op.drop_table("it_workflow_telemetry")
    op.drop_index("ix_request_events_event_type", table_name="request_events")
    op.drop_index("ix_request_events_request_id", table_name="request_events")
    op.drop_table("request_events")
    op.drop_index("ix_runbook_executions_request_id", table_name="runbook_executions")
    op.drop_table("runbook_executions")
    op.drop_index("ix_request_approvals_request_id", table_name="request_approvals")
    op.drop_table("request_approvals")
    op.drop_index("ix_request_entities_request_id", table_name="request_entities")
    op.drop_table("request_entities")
    op.drop_index("ix_it_requests_status", table_name="it_requests")
    op.drop_index("ix_it_requests_requester_id", table_name="it_requests")
    op.drop_table("it_requests")
    op.drop_table("access_catalog")
    op.drop_table("software_catalog")
    op.drop_table("runbooks")
    it_policy_decision.drop(op.get_bind(), checkfirst=True)
    it_execution_status.drop(op.get_bind(), checkfirst=True)
    it_approval_status.drop(op.get_bind(), checkfirst=True)
    it_risk_level.drop(op.get_bind(), checkfirst=True)
    it_request_status.drop(op.get_bind(), checkfirst=True)
    it_request_type.drop(op.get_bind(), checkfirst=True)
