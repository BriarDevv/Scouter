"""add mail credentials

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mail_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        # SMTP
        sa.Column("smtp_host", sa.String(), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("smtp_username", sa.String(), nullable=True),
        sa.Column("smtp_password", sa.String(), nullable=True),
        sa.Column("smtp_ssl", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("smtp_starttls", sa.Boolean(), nullable=False, server_default="true"),
        # IMAP
        sa.Column("imap_host", sa.String(), nullable=True),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("imap_username", sa.String(), nullable=True),
        sa.Column("imap_password", sa.String(), nullable=True),
        sa.Column("imap_ssl", sa.Boolean(), nullable=False, server_default="true"),
        # Test results
        sa.Column("smtp_last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("smtp_last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("smtp_last_test_error", sa.String(), nullable=True),
        sa.Column("imap_last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imap_last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("imap_last_test_error", sa.String(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mail_credentials")
