"""add investigation_threads and outcome_snapshots tables

Revision ID: h2b3c4d5e6f7
Revises: g1a2b3c4d5e6
Create Date: 2026-04-03 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h2b3c4d5e6f7"
down_revision: str | None = "g1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Investigation threads — Scout agent tool call history
    op.create_table(
        "investigation_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lead_id", sa.Uuid(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_run_id", sa.Uuid(), sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_model", sa.String(100), nullable=False),
        sa.Column("tool_calls_json", sa.JSON(), nullable=False),
        sa.Column("pages_visited_json", sa.JSON(), nullable=False),
        sa.Column("findings_json", sa.JSON(), nullable=False),
        sa.Column("loops_used", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_investigation_threads_lead_id", "investigation_threads", ["lead_id"])
    op.create_index("ix_investigation_threads_created_at", "investigation_threads", ["created_at"])

    # Outcome snapshots — pipeline state frozen at WON/LOST
    op.create_table(
        "outcome_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lead_id", sa.Uuid(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("lead_score", sa.Float(), nullable=True),
        sa.Column("lead_quality", sa.String(20), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("signals_json", sa.JSON(), nullable=True),
        sa.Column("pipeline_context_json", sa.JSON(), nullable=True),
        sa.Column("draft_channel", sa.String(20), nullable=True),
        sa.Column("reviewer_verdict", sa.String(50), nullable=True),
        sa.Column("corrections_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outcome_snapshots_lead_id", "outcome_snapshots", ["lead_id"])
    op.create_index("ix_outcome_snapshots_outcome", "outcome_snapshots", ["outcome"])
    op.create_index("ix_outcome_snapshots_created_at", "outcome_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_outcome_snapshots_created_at", table_name="outcome_snapshots")
    op.drop_index("ix_outcome_snapshots_outcome", table_name="outcome_snapshots")
    op.drop_index("ix_outcome_snapshots_lead_id", table_name="outcome_snapshots")
    op.drop_table("outcome_snapshots")
    op.drop_index("ix_investigation_threads_created_at", table_name="investigation_threads")
    op.drop_index("ix_investigation_threads_lead_id", table_name="investigation_threads")
    op.drop_table("investigation_threads")
