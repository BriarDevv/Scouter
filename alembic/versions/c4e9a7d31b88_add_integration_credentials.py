"""add integration_credentials table (google_maps_api_key)

Revision ID: c4e9a7d31b88
Revises: 8cd3ff7af6e0
Create Date: 2026-04-11 23:15:54.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e9a7d31b88"
down_revision: str | None = "8cd3ff7af6e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("google_maps_api_key", sa.String(length=500), nullable=True),
        sa.Column(
            "google_maps_api_key_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Insert the singleton row so services that do get_or_create never race.
    op.execute("INSERT INTO integration_credentials (id, updated_at) VALUES (1, CURRENT_TIMESTAMP)")


def downgrade() -> None:
    op.drop_table("integration_credentials")
