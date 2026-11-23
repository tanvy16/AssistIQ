"""Ticketing tables and SLA policies.

Revision ID: 0004_ticketing
Revises: 0003_auth_audit_events
Create Date: 2026-08-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_ticketing"
down_revision: Union[str, None] = "0003_auth_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ticket_priority_enum = postgresql.ENUM(
    "low", "medium", "high", "critical", name="ticket_priority", create_type=False
)
ticket_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "pending",
    "resolved",
    "closed",
    name="ticket_status",
    create_type=False,
)
ticket_category_enum = postgresql.ENUM(
    "network",
    "access",
    "hardware",
    "software",
    "other",
    name="ticket_category",
    create_type=False,
)


def upgrade() -> None:
    ticket_priority_enum.create(op.get_bind(), checkfirst=True)
    ticket_status_enum.create(op.get_bind(), checkfirst=True)
    ticket_category_enum.create(op.get_bind(), checkfirst=True)

    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START 1"))

    op.create_table(
        "sla_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("response_time_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_time_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("priority"),
    )

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_number", sa.String(length=16), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", ticket_category_enum, nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("status", ticket_status_enum, nullable=False),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_rationale", sa.Text(), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_tickets_ticket_number", "tickets", ["ticket_number"])
    op.create_index("ix_tickets_requester_id", "tickets", ["requester_id"])
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_sla_due_at", "tickets", ["sla_due_at"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])

    op.create_table(
        "ticket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])
    op.create_index("ix_ticket_events_created_at", "ticket_events", ["created_at"])

    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"])
    op.create_index("ix_ticket_comments_created_at", "ticket_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ticket_comments_created_at", table_name="ticket_comments")
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")
    op.drop_index("ix_ticket_events_created_at", table_name="ticket_events")
    op.drop_index("ix_ticket_events_ticket_id", table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_sla_due_at", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_assignee_id", table_name="tickets")
    op.drop_index("ix_tickets_requester_id", table_name="tickets")
    op.drop_index("ix_tickets_ticket_number", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("sla_policies")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS ticket_number_seq"))
    ticket_category_enum.drop(op.get_bind(), checkfirst=True)
    ticket_status_enum.drop(op.get_bind(), checkfirst=True)
    ticket_priority_enum.drop(op.get_bind(), checkfirst=True)
