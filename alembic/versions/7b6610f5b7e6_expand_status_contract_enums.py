"""expand status contract enums

Revision ID: 7b6610f5b7e6
Revises: 955a04d99157
Create Date: 2026-03-12 19:25:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7b6610f5b7e6"
down_revision: Union[str, None] = "955a04d99157"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_LEAD_STATUS_VALUES = (
    "QUALIFIED",
    "OPENED",
    "REPLIED",
    "MEETING",
    "WON",
    "LOST",
)

NEW_LOG_ACTION_VALUES = (
    "OPENED",
    "REPLIED",
    "MEETING",
    "WON",
    "LOST",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for value in NEW_LEAD_STATUS_VALUES:
        op.execute(f"ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS '{value}'")

    for value in NEW_LOG_ACTION_VALUES:
        op.execute(f"ALTER TYPE logaction ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        UPDATE leads
        SET status = CASE status
            WHEN 'QUALIFIED' THEN 'SCORED'
            WHEN 'OPENED' THEN 'CONTACTED'
            WHEN 'REPLIED' THEN 'CONTACTED'
            WHEN 'MEETING' THEN 'CONTACTED'
            WHEN 'WON' THEN 'CONTACTED'
            WHEN 'LOST' THEN 'CONTACTED'
            ELSE status
        END
        """
    )
    op.execute(
        """
        UPDATE outreach_logs
        SET action = CASE action
            WHEN 'OPENED' THEN 'SENT'
            WHEN 'REPLIED' THEN 'SENT'
            WHEN 'MEETING' THEN 'SENT'
            WHEN 'WON' THEN 'SENT'
            WHEN 'LOST' THEN 'SENT'
            ELSE action
        END
        """
    )

    op.execute(
        """
        CREATE TYPE leadstatus_old AS ENUM (
            'NEW',
            'ENRICHED',
            'SCORED',
            'DRAFT_READY',
            'APPROVED',
            'CONTACTED',
            'SUPPRESSED'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE leads
        ALTER COLUMN status TYPE leadstatus_old
        USING status::text::leadstatus_old
        """
    )
    op.execute("DROP TYPE leadstatus")
    op.execute("ALTER TYPE leadstatus_old RENAME TO leadstatus")

    op.execute(
        """
        CREATE TYPE logaction_old AS ENUM (
            'GENERATED',
            'REVIEWED',
            'APPROVED',
            'REJECTED',
            'SENT'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE outreach_logs
        ALTER COLUMN action TYPE logaction_old
        USING action::text::logaction_old
        """
    )
    op.execute("DROP TYPE logaction")
    op.execute("ALTER TYPE logaction_old RENAME TO logaction")
