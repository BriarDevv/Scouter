"""add whatsapp_outreach_enabled to operational settings

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-03-29 01:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("operational_settings",
        sa.Column("whatsapp_outreach_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))

def downgrade() -> None:
    op.drop_column("operational_settings", "whatsapp_outreach_enabled")
