"""add slack alert settings to operational_settings

Revision ID: m7h8i9j0k1l2
Revises: l6f7g8h9i0j1
Create Date: 2026-04-13 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m7h8i9j0k1l2"
down_revision: str | None = "l6f7g8h9i0j1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operational_settings",
        sa.Column(
            "slack_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "operational_settings",
        sa.Column("slack_webhook_url", sa.String(), nullable=True),
    )
    op.add_column(
        "operational_settings",
        sa.Column(
            "slack_min_severity",
            sa.String(),
            nullable=False,
            server_default="high",
        ),
    )


def downgrade() -> None:
    op.drop_column("operational_settings", "slack_min_severity")
    op.drop_column("operational_settings", "slack_webhook_url")
    op.drop_column("operational_settings", "slack_alerts_enabled")
