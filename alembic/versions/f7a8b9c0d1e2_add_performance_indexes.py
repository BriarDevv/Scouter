"""add performance indexes on outreach and inbound tables

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-28 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = [
    ("ix_outreach_drafts_lead_id", "outreach_drafts", ["lead_id"]),
    ("ix_outreach_drafts_status", "outreach_drafts", ["status"]),
    ("ix_outreach_drafts_generated_at", "outreach_drafts", ["generated_at"]),
    ("ix_outreach_logs_lead_id", "outreach_logs", ["lead_id"]),
    ("ix_outreach_logs_created_at", "outreach_logs", ["created_at"]),
    ("ix_inbound_messages_received_at", "inbound_messages", ["received_at"]),
    ("ix_inbound_messages_classification_status", "inbound_messages", ["classification_status"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, _table, _columns in _INDEXES:
        op.drop_index(name)
