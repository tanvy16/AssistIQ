"""Chat conversations, messages, citations, and escalations.

Revision ID: 0007_chat_and_rag_conversations
Revises: 0006_ai_modeling
Create Date: 2026-08-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_chat_and_rag_conversations"
down_revision: Union[str, None] = "0006_ai_modeling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

conversation_status_enum = postgresql.ENUM(
    "active", "escalated", "closed", name="conversation_status", create_type=False
)
chat_message_role_enum = postgresql.ENUM(
    "user", "assistant", "system", name="chat_message_role", create_type=False
)
confidence_state_enum = postgresql.ENUM(
    "HIGH_CONFIDENCE",
    "LOW_CONFIDENCE",
    "NO_EVIDENCE",
    name="confidence_state",
    create_type=False,
)
escalation_status_enum = postgresql.ENUM(
    "open", "resolved", name="escalation_status", create_type=False
)


def upgrade() -> None:
    conversation_status_enum.create(op.get_bind(), checkfirst=True)
    chat_message_role_enum.create(op.get_bind(), checkfirst=True)
    confidence_state_enum.create(op.get_bind(), checkfirst=True)
    escalation_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", conversation_status_enum, nullable=False),
        sa.Column("selected_model_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["selected_model_id"], ["ai_model_registry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", chat_message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("confidence_state", confidence_state_enum, nullable=True),
        sa.Column("message_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["ai_model_registry.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    op.create_table(
        "message_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("citation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])

    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("status", escalation_status_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_escalations_conversation_id", "escalations", ["conversation_id"])
    op.create_index("ix_escalations_status", "escalations", ["status"])

    op.create_table(
        "chat_interaction_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("retrieval_latency_ms", sa.Float(), nullable=True),
        sa.Column("generation_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("retrieved_count", sa.Integer(), nullable=True),
        sa.Column("top_similarity_score", sa.Float(), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("confidence_state", sa.String(length=32), nullable=True),
        sa.Column("escalation_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("telemetry_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_interaction_telemetry_conversation_id",
        "chat_interaction_telemetry",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_interaction_telemetry_conversation_id", table_name="chat_interaction_telemetry")
    op.drop_table("chat_interaction_telemetry")
    op.drop_index("ix_escalations_status", table_name="escalations")
    op.drop_index("ix_escalations_conversation_id", table_name="escalations")
    op.drop_table("escalations")
    op.drop_index("ix_message_citations_message_id", table_name="message_citations")
    op.drop_table("message_citations")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    escalation_status_enum.drop(op.get_bind(), checkfirst=True)
    confidence_state_enum.drop(op.get_bind(), checkfirst=True)
    chat_message_role_enum.drop(op.get_bind(), checkfirst=True)
    conversation_status_enum.drop(op.get_bind(), checkfirst=True)
