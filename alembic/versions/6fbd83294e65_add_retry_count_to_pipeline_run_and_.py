"""add retry_count to pipeline_run and dead_letter_tasks table

Revision ID: 6fbd83294e65
Revises: cda23d64089b
Create Date: 2026-04-13 17:25:02.300147

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6fbd83294e65"
down_revision: str | None = "cda23d64089b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dead_letter_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("pipeline_run_id", sa.Uuid(), nullable=True),
        sa.Column("step", sa.String(length=50), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "retry_count")
    op.drop_table("dead_letter_tasks")
