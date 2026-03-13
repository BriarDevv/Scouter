"""add inbound mail tables

Revision ID: f2c3b93f2e58
Revises: 2b6d8800aef8
Create Date: 2026-03-13 11:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c3b93f2e58"
down_revision: Union[str, None] = "2b6d8800aef8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_outreach_deliveries_provider_message_id",
        "outreach_deliveries",
        ["provider_message_id"],
        unique=False,
    )

    op.create_table(
        "inbound_mail_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_mailbox", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("deduplicated_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("unmatched_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inbound_mail_sync_runs_created_at",
        "inbound_mail_sync_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_inbound_mail_sync_runs_status",
        "inbound_mail_sync_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "email_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("draft_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_mailbox", sa.String(length=255), nullable=False),
        sa.Column("external_thread_id", sa.String(length=255), nullable=True),
        sa.Column("thread_key", sa.String(length=512), nullable=False),
        sa.Column("matched_via", sa.String(length=50), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["outreach_deliveries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["draft_id"], ["outreach_drafts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_mailbox",
            "thread_key",
            name="uq_email_threads_provider_mailbox_thread_key",
        ),
    )
    op.create_index("ix_email_threads_delivery_id", "email_threads", ["delivery_id"], unique=False)
    op.create_index("ix_email_threads_last_message_at", "email_threads", ["last_message_at"], unique=False)
    op.create_index("ix_email_threads_lead_id", "email_threads", ["lead_id"], unique=False)

    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("draft_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_mailbox", sa.String(length=255), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("references_raw", sa.Text(), nullable=True),
        sa.Column("from_email", sa.String(length=320), nullable=True),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("to_email", sa.String(length=500), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_snippet", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata_json", sa.JSON(), nullable=True),
        sa.Column("classification_status", sa.String(length=50), nullable=False),
        sa.Column("classification_label", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("next_action_suggestion", sa.Text(), nullable=True),
        sa.Column("should_escalate_reviewer", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["outreach_deliveries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["draft_id"], ["outreach_drafts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_inbound_messages_dedupe_key"),
    )
    op.create_index(
        "ix_inbound_messages_classification_label",
        "inbound_messages",
        ["classification_label"],
        unique=False,
    )
    op.create_index(
        "ix_inbound_messages_classification_status",
        "inbound_messages",
        ["classification_status"],
        unique=False,
    )
    op.create_index("ix_inbound_messages_delivery_id", "inbound_messages", ["delivery_id"], unique=False)
    op.create_index("ix_inbound_messages_lead_id", "inbound_messages", ["lead_id"], unique=False)
    op.create_index("ix_inbound_messages_message_id", "inbound_messages", ["message_id"], unique=False)
    op.create_index(
        "ix_inbound_messages_provider_message_id",
        "inbound_messages",
        ["provider_message_id"],
        unique=False,
    )
    op.create_index("ix_inbound_messages_received_at", "inbound_messages", ["received_at"], unique=False)
    op.create_index("ix_inbound_messages_thread_id", "inbound_messages", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inbound_messages_thread_id", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_received_at", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_provider_message_id", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_message_id", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_lead_id", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_delivery_id", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_classification_status", table_name="inbound_messages")
    op.drop_index("ix_inbound_messages_classification_label", table_name="inbound_messages")
    op.drop_table("inbound_messages")

    op.drop_index("ix_email_threads_lead_id", table_name="email_threads")
    op.drop_index("ix_email_threads_last_message_at", table_name="email_threads")
    op.drop_index("ix_email_threads_delivery_id", table_name="email_threads")
    op.drop_table("email_threads")

    op.drop_index("ix_inbound_mail_sync_runs_status", table_name="inbound_mail_sync_runs")
    op.drop_index("ix_inbound_mail_sync_runs_created_at", table_name="inbound_mail_sync_runs")
    op.drop_table("inbound_mail_sync_runs")

    op.drop_index(
        "ix_outreach_deliveries_provider_message_id", table_name="outreach_deliveries"
    )
