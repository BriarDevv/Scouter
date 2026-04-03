"""add operational state fields to task runs

Revision ID: c6d7e8f9a0b1
Revises: b4c5d6e7f8a9
Create Date: 2026-04-03 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: str | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task_runs", sa.Column("scope_key", sa.String(length=255), nullable=True))
    op.add_column("task_runs", sa.Column("progress_json", sa.JSON(), nullable=True))
    op.add_column(
        "task_runs",
        sa.Column("stop_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_task_runs_task_name_scope_key",
        "task_runs",
        ["task_name", "scope_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_runs_task_name_scope_key", table_name="task_runs")
    op.drop_column("task_runs", "stop_requested_at")
    op.drop_column("task_runs", "progress_json")
    op.drop_column("task_runs", "scope_key")
