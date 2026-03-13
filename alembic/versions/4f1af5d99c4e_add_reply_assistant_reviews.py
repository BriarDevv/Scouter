"""add reply assistant reviews

Revision ID: 4f1af5d99c4e
Revises: c8b6e42d1f9a
Create Date: 2026-03-14 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f1af5d99c4e"
down_revision: Union[str, None] = "c8b6e42d1f9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reply_assistant_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reply_assistant_draft_id", sa.Uuid(), nullable=False),
        sa.Column("inbound_message_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "reviewed", "failed", name="replyassistantreviewstatus"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("suggested_edits", sa.JSON(), nullable=True),
        sa.Column("recommended_action", sa.String(length=64), nullable=True),
        sa.Column("should_use_as_is", sa.Boolean(), nullable=False),
        sa.Column("should_edit", sa.Boolean(), nullable=False),
        sa.Column("should_escalate", sa.Boolean(), nullable=False),
        sa.Column("reviewer_role", sa.String(length=50), nullable=True),
        sa.Column("reviewer_model", sa.String(length=255), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "reply_assistant_draft_id",
            name="uq_reply_assistant_reviews_reply_assistant_draft_id",
        ),
    )
    op.create_index(
        "ix_reply_assistant_reviews_inbound_message_id",
        "reply_assistant_reviews",
        ["inbound_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_reviews_lead_id",
        "reply_assistant_reviews",
        ["lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_reviews_thread_id",
        "reply_assistant_reviews",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_reviews_status",
        "reply_assistant_reviews",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_reviews_task_id",
        "reply_assistant_reviews",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_reply_assistant_reviews_updated_at",
        "reply_assistant_reviews",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reply_assistant_reviews_updated_at", table_name="reply_assistant_reviews")
    op.drop_index("ix_reply_assistant_reviews_task_id", table_name="reply_assistant_reviews")
    op.drop_index("ix_reply_assistant_reviews_status", table_name="reply_assistant_reviews")
    op.drop_index("ix_reply_assistant_reviews_thread_id", table_name="reply_assistant_reviews")
    op.drop_index("ix_reply_assistant_reviews_lead_id", table_name="reply_assistant_reviews")
    op.drop_index(
        "ix_reply_assistant_reviews_inbound_message_id",
        table_name="reply_assistant_reviews",
    )
    op.drop_table("reply_assistant_reviews")
    sa.Enum(name="replyassistantreviewstatus").drop(op.get_bind(), checkfirst=True)
