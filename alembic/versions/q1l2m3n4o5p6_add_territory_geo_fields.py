"""add territory geo fields (country_code, center_lat, center_lng, bbox)

Revision ID: q1l2m3n4o5p6
Revises: p0k1l2m3n4o5
Create Date: 2026-04-13 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q1l2m3n4o5p6"
down_revision: str | None = "p0k1l2m3n4o5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "territories",
        sa.Column(
            "country_code",
            sa.String(length=2),
            nullable=False,
            server_default="AR",
        ),
    )
    op.add_column(
        "territories",
        sa.Column("center_lat", sa.Float(), nullable=True),
    )
    op.add_column(
        "territories",
        sa.Column("center_lng", sa.Float(), nullable=True),
    )
    op.add_column(
        "territories",
        sa.Column("bbox", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("territories", "bbox")
    op.drop_column("territories", "center_lng")
    op.drop_column("territories", "center_lat")
    op.drop_column("territories", "country_code")
