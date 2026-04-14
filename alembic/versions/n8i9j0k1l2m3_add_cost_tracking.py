"""add cost tracking columns to llm_invocations + operational_settings

Revision ID: n8i9j0k1l2m3
Revises: m7h8i9j0k1l2
Create Date: 2026-04-13 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n8i9j0k1l2m3"
down_revision: str | None = "m7h8i9j0k1l2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "llm_invocations",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "llm_invocations",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "llm_invocations",
        sa.Column("usd_cost_estimated", sa.Float(), nullable=True),
    )
    op.add_column(
        "operational_settings",
        sa.Column("daily_usd_budget", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "daily_usd_budget")
    op.drop_column("llm_invocations", "usd_cost_estimated")
    op.drop_column("llm_invocations", "completion_tokens")
    op.drop_column("llm_invocations", "prompt_tokens")
