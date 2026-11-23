"""AI model registry, inference, and evaluation tables.

Revision ID: 0006_ai_modeling
Revises: 0005_knowledge_base
Create Date: 2026-08-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_ai_modeling"
down_revision: Union[str, None] = "0005_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ai_model_type_enum = postgresql.ENUM(
    "lightweight_ml",
    "deep_learning",
    "llm",
    name="ai_model_type",
    create_type=False,
)
ai_evaluation_type_enum = postgresql.ENUM(
    "classification",
    "regression",
    "llm_generation",
    name="ai_evaluation_type",
    create_type=False,
)


def upgrade() -> None:
    ai_model_type_enum.create(op.get_bind(), checkfirst=True)
    ai_evaluation_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_key", sa.String(length=64), nullable=False),
        sa.Column("model_type", ai_model_type_enum, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("config_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.UniqueConstraint("model_key"),
    )
    op.create_index("ix_ai_model_registry_model_type", "ai_model_registry", ["model_type"])
    op.create_index("ix_ai_model_registry_model_key", "ai_model_registry", ["model_key"])

    op.create_table(
        "ai_inference_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_type", ai_model_type_enum, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_key", sa.String(length=64), nullable=True),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("input_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("inference_units", sa.Integer(), nullable=True),
        sa.Column("telemetry_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["model_registry_id"], ["ai_model_registry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_ai_inference_telemetry_created_at", "ai_inference_telemetry", ["created_at"]
    )
    op.create_index(
        "ix_ai_inference_telemetry_model_type", "ai_inference_telemetry", ["model_type"]
    )

    op.create_table(
        "ai_evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_registry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_type", ai_evaluation_type_enum, nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dataset_ref", sa.String(length=255), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["model_registry_id"], ["ai_model_registry.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_evaluation_results_model_registry_id",
        "ai_evaluation_results",
        ["model_registry_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_evaluation_results_model_registry_id", table_name="ai_evaluation_results")
    op.drop_table("ai_evaluation_results")
    op.drop_index("ix_ai_inference_telemetry_model_type", table_name="ai_inference_telemetry")
    op.drop_index("ix_ai_inference_telemetry_created_at", table_name="ai_inference_telemetry")
    op.drop_table("ai_inference_telemetry")
    op.drop_index("ix_ai_model_registry_model_key", table_name="ai_model_registry")
    op.drop_index("ix_ai_model_registry_model_type", table_name="ai_model_registry")
    op.drop_table("ai_model_registry")
    ai_evaluation_type_enum.drop(op.get_bind(), checkfirst=True)
    ai_model_type_enum.drop(op.get_bind(), checkfirst=True)
