"""add google maps fields to leads

Revision ID: b2c3d4e5f6a7
Revises: a5cc6250a134
Create Date: 2026-03-14 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a5cc6250a134"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("google_maps_url", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("rating", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("review_count", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("business_status", sa.String(50), nullable=True))
    op.add_column("leads", sa.Column("opening_hours", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "opening_hours")
    op.drop_column("leads", "business_status")
    op.drop_column("leads", "review_count")
    op.drop_column("leads", "rating")
    op.drop_column("leads", "google_maps_url")
    op.drop_column("leads", "address")
