"""add website_error signal type

Revision ID: b9a5c4095864
Revises: 64d90f18d551
Create Date: 2026-03-24 20:05:12.090420

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b9a5c4095864'
down_revision: Union[str, None] = '64d90f18d551'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE signaltype ADD VALUE IF NOT EXISTS 'website_error'")


def downgrade() -> None:
    pass  # PostgreSQL doesn't support removing enum values
