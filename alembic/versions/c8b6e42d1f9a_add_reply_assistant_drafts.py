"""add reply assistant drafts

Revision ID: c8b6e42d1f9a
Revises: b3d8a9b3c6f1
Create Date: 2026-03-13 22:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8b6e42d1f9a"
down_revision: Union[str, None] = "b3d8a9b3c6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reply_assistant_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inbound_message_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("related_delivery_id", sa.Uuid(), nullable=True),
        sa.Column("related_outbound_draft_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("generated", name="replyassistantdraftstatus"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("suggested_tone", sa.String(length=50), nullable=True),
        sa.Column("should_escalate_reviewer", sa.Boolean(), nullable=False),
        sa.Column("generator_role", sa.String(length=50), nullable=False),
        sa.Column("generator_model", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["inbound_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["related_delivery_id"], ["outreach_deliveries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["related_outbound_draft_id"], ["outreach_drafts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "inbound_message_id",
            name="uq_reply_assistant_drafts_inbound_message_id",
        ),
    )
    op.create_index(
        "ix_reply_assistant_drafts_lead_id",
        "reply_assistant_drafts",
        ["lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_drafts_thread_id",
        "reply_assistant_drafts",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_drafts_delivery_id",
        "reply_assistant_drafts",
        ["related_delivery_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_drafts_outbound_draft_id",
        "reply_assistant_drafts",
        ["related_outbound_draft_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_drafts_updated_at",
        "reply_assistant_drafts",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reply_assistant_drafts_updated_at", table_name="reply_assistant_drafts")
    op.drop_index(
        "ix_reply_assistant_drafts_outbound_draft_id",
        table_name="reply_assistant_drafts",
    )
    op.drop_index("ix_reply_assistant_drafts_delivery_id", table_name="reply_assistant_drafts")
    op.drop_index("ix_reply_assistant_drafts_thread_id", table_name="reply_assistant_drafts")
    op.drop_index("ix_reply_assistant_drafts_lead_id", table_name="reply_assistant_drafts")
    op.drop_table("reply_assistant_drafts")
    sa.Enum(name="replyassistantdraftstatus").drop(op.get_bind(), checkfirst=True)
