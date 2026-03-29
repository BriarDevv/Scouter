"""add operational settings table with auto-crawl fields

Revision ID: b3c8d7e9f1a2
Revises: 0f5fef81f0ae
Create Date: 2026-03-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c8d7e9f1a2"
down_revision: Union[str, None] = "0f5fef81f0ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("auto_crawl_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_crawl_threshold", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("auto_crawl_territory_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("operational_settings")
