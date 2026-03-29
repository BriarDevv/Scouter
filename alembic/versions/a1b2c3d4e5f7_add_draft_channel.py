"""add channel column to outreach_drafts

Revision ID: a1b2c3d4e5f7
Revises: f7a8b9c0d1e2
Create Date: 2026-03-28 23:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_drafts",
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
    )
    op.alter_column("outreach_drafts", "subject", nullable=True)


def downgrade() -> None:
    op.alter_column("outreach_drafts", "subject", nullable=False)
    op.drop_column("outreach_drafts", "channel")
