"""add agent enabled flags to operational settings

Revision ID: d5e6f7a8b9c0
Revises: c1d2e3f4a5b6
Create Date: 2026-03-28 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column("telegram_agent_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "operational_settings",
        sa.Column("whatsapp_agent_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "whatsapp_agent_enabled")
    op.drop_column("operational_settings", "telegram_agent_enabled")
