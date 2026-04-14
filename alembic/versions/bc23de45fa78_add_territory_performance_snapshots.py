"""add territory performance snapshots table

Revision ID: bc23de45fa78
Revises: ab12cd34ef56
Create Date: 2026-04-13 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "bc23de45fa78"
down_revision: str | None = "ab12cd34ef56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "territory_performance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("territory_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("leads_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_qualified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_contacted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_lost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["territory_id"], ["territories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_territory_performance_territory_id",
        "territory_performance_snapshots",
        ["territory_id"],
    )
    op.create_index(
        "ix_territory_performance_period_end",
        "territory_performance_snapshots",
        ["period_end"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_territory_performance_period_end", table_name="territory_performance_snapshots"
    )
    op.drop_index(
        "ix_territory_performance_territory_id", table_name="territory_performance_snapshots"
    )
    op.drop_table("territory_performance_snapshots")
