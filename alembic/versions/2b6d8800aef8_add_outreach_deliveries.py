"""add outreach deliveries

Revision ID: 2b6d8800aef8
Revises: 0f5fef81f0ae
Create Date: 2026-03-13 06:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b6d8800aef8"
down_revision: Union[str, None] = "0f5fef81f0ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outreach_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("subject_snapshot", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("sending", "sent", "failed", name="outreachdeliverystatus"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["outreach_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outreach_deliveries_draft_id", "outreach_deliveries", ["draft_id"], unique=False)
    op.create_index("ix_outreach_deliveries_lead_id", "outreach_deliveries", ["lead_id"], unique=False)
    op.create_index("ix_outreach_deliveries_status", "outreach_deliveries", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_outreach_deliveries_status", table_name="outreach_deliveries")
    op.drop_index("ix_outreach_deliveries_lead_id", table_name="outreach_deliveries")
    op.drop_index("ix_outreach_deliveries_draft_id", table_name="outreach_deliveries")
    op.drop_table("outreach_deliveries")
    op.execute("DROP TYPE IF EXISTS outreachdeliverystatus")
