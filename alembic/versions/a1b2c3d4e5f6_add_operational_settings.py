"""add operational settings

Revision ID: a1b2c3d4e5f6
Revises: 4f1af5d99c4e
Create Date: 2026-03-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4f1af5d99c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("signature_name", sa.String(), nullable=True),
        sa.Column("signature_role", sa.String(), nullable=True),
        sa.Column("signature_company", sa.String(), nullable=True),
        sa.Column("portfolio_url", sa.String(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("calendar_url", sa.String(), nullable=True),
        sa.Column("signature_cta", sa.String(), nullable=True),
        sa.Column("signature_include_portfolio", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("default_outreach_tone", sa.String(), nullable=False, server_default="profesional"),
        sa.Column("default_reply_tone", sa.String(), nullable=False, server_default="profesional"),
        sa.Column("default_closing_line", sa.String(), nullable=True),
        sa.Column("mail_enabled", sa.Boolean(), nullable=True),
        sa.Column("mail_from_email", sa.String(), nullable=True),
        sa.Column("mail_from_name", sa.String(), nullable=True),
        sa.Column("mail_reply_to", sa.String(), nullable=True),
        sa.Column("mail_send_timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("require_approved_drafts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("mail_inbound_sync_enabled", sa.Boolean(), nullable=True),
        sa.Column("mail_inbound_mailbox", sa.String(), nullable=True),
        sa.Column("mail_inbound_sync_limit", sa.Integer(), nullable=True),
        sa.Column("mail_inbound_timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("mail_inbound_search_criteria", sa.String(), nullable=True),
        sa.Column("auto_classify_inbound", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reply_assistant_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reviewer_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewer_labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reviewer_confidence_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("prioritize_quote_replies", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("prioritize_meeting_replies", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_openclaw_briefs", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_reply_assistant_generation", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("use_reviewer_for_labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("operational_settings")
