"""add reply assistant sends

Revision ID: 9d4e1a2b7c3d
Revises: 4f1af5d99c4e
Create Date: 2026-03-14 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d4e1a2b7c3d"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reply_assistant_drafts",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reply_assistant_drafts",
        sa.Column("edited_by", sa.String(length=100), nullable=True),
    )

    op.create_table(
        "reply_assistant_sends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reply_assistant_draft_id", sa.Uuid(), nullable=False),
        sa.Column("inbound_message_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("sending", "sent", "failed", name="replyassistantsendstatus"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("from_email_snapshot", sa.String(length=320), nullable=True),
        sa.Column("reply_to_snapshot", sa.String(length=320), nullable=True),
        sa.Column("subject_snapshot", sa.String(length=500), nullable=False),
        sa.Column("body_snapshot", sa.Text(), nullable=False),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("references_raw", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reply_assistant_draft_id"],
            ["reply_assistant_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["inbound_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reply_assistant_sends_draft_id",
        "reply_assistant_sends",
        ["reply_assistant_draft_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_inbound_message_id",
        "reply_assistant_sends",
        ["inbound_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_thread_id",
        "reply_assistant_sends",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_lead_id",
        "reply_assistant_sends",
        ["lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_status",
        "reply_assistant_sends",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_provider_message_id",
        "reply_assistant_sends",
        ["provider_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_sends_created_at",
        "reply_assistant_sends",
        ["created_at"],
        unique=False,
    )

    bind = op.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "postgresql":
        op.create_index(
            "uq_reply_assistant_sends_active_or_sent_per_draft",
            "reply_assistant_sends",
            ["reply_assistant_draft_id"],
            unique=True,
            postgresql_where=sa.text("status IN ('sending', 'sent')"),
        )
    elif dialect_name == "sqlite":
        op.create_index(
            "uq_reply_assistant_sends_active_or_sent_per_draft",
            "reply_assistant_sends",
            ["reply_assistant_draft_id"],
            unique=True,
            sqlite_where=sa.text("status IN ('sending', 'sent')"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name in {"postgresql", "sqlite"}:
        op.drop_index(
            "uq_reply_assistant_sends_active_or_sent_per_draft",
            table_name="reply_assistant_sends",
        )
    op.drop_index("ix_reply_assistant_sends_created_at", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_provider_message_id", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_status", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_lead_id", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_thread_id", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_inbound_message_id", table_name="reply_assistant_sends")
    op.drop_index("ix_reply_assistant_sends_draft_id", table_name="reply_assistant_sends")
    op.drop_table("reply_assistant_sends")
    op.drop_column("reply_assistant_drafts", "edited_by")
    op.drop_column("reply_assistant_drafts", "edited_at")
    sa.Enum(name="replyassistantsendstatus").drop(op.get_bind(), checkfirst=True)
