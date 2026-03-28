"""remove openclaw and old keyword system settings

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-28 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS_TO_DROP = [
    "openclaw_model",
    "openclaw_max_response_chars",
    "openclaw_rate_limit",
    "openclaw_rate_window_seconds",
    "whatsapp_openclaw_enrichment",
    "whatsapp_conversational_enabled",
    "whatsapp_actions_enabled",
    "telegram_openclaw_enrichment",
    "telegram_conversational_enabled",
    "telegram_actions_enabled",
]


def upgrade() -> None:
    for col in _COLUMNS_TO_DROP:
        op.drop_column("operational_settings", col)


def downgrade() -> None:
    op.add_column("operational_settings",
        sa.Column("openclaw_model", sa.String(), nullable=False, server_default="leader"))
    op.add_column("operational_settings",
        sa.Column("openclaw_max_response_chars", sa.Integer(), nullable=False, server_default="600"))
    op.add_column("operational_settings",
        sa.Column("openclaw_rate_limit", sa.Integer(), nullable=False, server_default="20"))
    op.add_column("operational_settings",
        sa.Column("openclaw_rate_window_seconds", sa.Integer(), nullable=False, server_default="900"))
    op.add_column("operational_settings",
        sa.Column("whatsapp_openclaw_enrichment", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("operational_settings",
        sa.Column("whatsapp_conversational_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("operational_settings",
        sa.Column("whatsapp_actions_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("operational_settings",
        sa.Column("telegram_openclaw_enrichment", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("operational_settings",
        sa.Column("telegram_conversational_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("operational_settings",
        sa.Column("telegram_actions_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
