"""add lead_events table

Revision ID: p0k1l2m3n4o5
Revises: o9j0k1l2m3n4
Create Date: 2026-04-13 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "p0k1l2m3n4o5"
down_revision: str | None = "o9j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "actor",
            sa.String(length=64),
            nullable=False,
            server_default="system",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lead_events_lead_id_created_at_desc",
        "lead_events",
        ["lead_id", "created_at"],
    )
    op.create_index(
        "ix_lead_events_event_type",
        "lead_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_lead_events_event_type", table_name="lead_events")
    op.drop_index("ix_lead_events_lead_id_created_at_desc", table_name="lead_events")
    op.drop_table("lead_events")
