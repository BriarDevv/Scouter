"""add followup_days to operational_settings

Revision ID: o9j0k1l2m3n4
Revises: n8i9j0k1l2m3
Create Date: 2026-04-13 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o9j0k1l2m3n4"
down_revision: str | None = "n8i9j0k1l2m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column(
            "followup_days",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "followup_days")
