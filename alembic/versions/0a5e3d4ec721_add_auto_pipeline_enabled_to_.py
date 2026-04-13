"""add auto_pipeline_enabled to operational_settings

Revision ID: 0a5e3d4ec721
Revises: k5e6f7g8h9i0
Create Date: 2026-04-13 17:11:19.268675

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a5e3d4ec721"
down_revision: str | None = "k5e6f7g8h9i0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column("auto_pipeline_enabled", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "auto_pipeline_enabled")
