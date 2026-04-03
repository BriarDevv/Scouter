"""add outreach generation metadata

Revision ID: b4c5d6e7f8a9
Revises: a0d285b111e7
Create Date: 2026-04-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a0d285b111e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_drafts",
        sa.Column("generation_metadata_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outreach_drafts", "generation_metadata_json")
