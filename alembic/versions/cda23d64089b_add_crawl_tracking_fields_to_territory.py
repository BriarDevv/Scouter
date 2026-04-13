"""add crawl tracking fields to territory

Revision ID: cda23d64089b
Revises: 0a5e3d4ec721
Create Date: 2026-04-13 17:16:50.465586

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cda23d64089b"
down_revision: str | None = "0a5e3d4ec721"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "territories", sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("territories", sa.Column("last_dup_ratio", sa.Float(), nullable=True))
    op.add_column(
        "territories", sa.Column("crawl_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "territories",
        sa.Column("is_saturated", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("territories", "is_saturated")
    op.drop_column("territories", "crawl_count")
    op.drop_column("territories", "last_dup_ratio")
    op.drop_column("territories", "last_crawled_at")
