"""add outbound_conversations table

Revision ID: i3c4d5e6f7g8
Revises: h2b3c4d5e6f7
Create Date: 2026-04-04 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i3c4d5e6f7g8"
down_revision: str | None = "h2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbound_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lead_id", sa.Uuid(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_id", sa.Uuid(), sa.ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft_ready", "sent", "delivered", "replied",
                "meeting", "closed", "operator_took_over",
                name="conversationstatus",
            ),
            nullable=False,
            server_default="draft_ready",
        ),
        sa.Column("messages_json", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="outreach"),
        sa.Column("operator_took_over", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outbound_conversations_lead_id", "outbound_conversations", ["lead_id"])
    op.create_index("ix_outbound_conversations_status", "outbound_conversations", ["status"])
    op.create_index("ix_outbound_conversations_created_at", "outbound_conversations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbound_conversations_created_at", table_name="outbound_conversations")
    op.drop_index("ix_outbound_conversations_status", table_name="outbound_conversations")
    op.drop_index("ix_outbound_conversations_lead_id", table_name="outbound_conversations")
    op.drop_table("outbound_conversations")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
