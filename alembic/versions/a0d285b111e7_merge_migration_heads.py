"""merge migration heads

Revision ID: a0d285b111e7
Revises: a2b3c4d5e6f8, c3d4e5f6a7b9
Create Date: 2026-04-02 21:57:57.572971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0d285b111e7'
down_revision: Union[str, None] = ('a2b3c4d5e6f8', 'c3d4e5f6a7b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commercial_briefs",
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("commercial_briefs", "is_fallback")
