"""add llm invocations table

Revision ID: f8e9d0c1b2a3
Revises: c6d7e8f9a0b1
Create Date: 2026-04-03 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f8e9d0c1b2a3"
down_revision: str | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_invocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("function_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_id", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "succeeded",
                "degraded",
                "fallback",
                "parse_failed",
                "failed",
                name="llminvocationstatus",
            ),
            nullable=False,
        ),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("parse_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("pipeline_run_id", sa.String(length=64), nullable=True),
        sa.Column("lead_id", sa.String(length=64), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_invocations_prompt_id", "llm_invocations", ["prompt_id"], unique=False)
    op.create_index("ix_llm_invocations_status", "llm_invocations", ["status"], unique=False)
    op.create_index(
        "ix_llm_invocations_target_type_target_id",
        "llm_invocations",
        ["target_type", "target_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_invocations_correlation_id",
        "llm_invocations",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_invocations_created_at",
        "llm_invocations",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_invocations_created_at", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_correlation_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_target_type_target_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_status", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_prompt_id", table_name="llm_invocations")
    op.drop_table("llm_invocations")
