"""drop allow_openclaw_briefs column

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-04-01 23:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("operational_settings", "allow_openclaw_briefs")


def downgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column("allow_openclaw_briefs", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
