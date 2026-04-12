"""add kapso_api_key to integration_credentials

Revision ID: k5e6f7g8h9i0
Revises: j4d5e6f7g8h9
Create Date: 2026-04-12 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k5e6f7g8h9i0"
down_revision: str | None = "c4e9a7d31b88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integration_credentials",
        sa.Column("kapso_api_key", sa.String(500), nullable=True),
    )
    op.add_column(
        "integration_credentials",
        sa.Column("kapso_api_key_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("integration_credentials", "kapso_api_key_updated_at")
    op.drop_column("integration_credentials", "kapso_api_key")
