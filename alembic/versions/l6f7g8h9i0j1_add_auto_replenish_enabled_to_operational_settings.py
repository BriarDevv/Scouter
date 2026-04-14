"""add auto_replenish_enabled to operational_settings

Revision ID: l6f7g8h9i0j1
Revises: bc23de45fa78
Create Date: 2026-04-13 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l6f7g8h9i0j1"
down_revision: str | None = "bc23de45fa78"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column(
            "auto_replenish_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "auto_replenish_enabled")
