"""add inbound classification trace

Revision ID: b3d8a9b3c6f1
Revises: f2c3b93f2e58
Create Date: 2026-03-13 12:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3d8a9b3c6f1"
down_revision: Union[str, None] = "f2c3b93f2e58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inbound_messages", sa.Column("classification_error", sa.Text(), nullable=True))
    op.add_column("inbound_messages", sa.Column("classification_role", sa.String(length=50), nullable=True))
    op.add_column(
        "inbound_messages",
        sa.Column("classification_model", sa.String(length=255), nullable=True),
    )
    op.add_column("inbound_messages", sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE inbound_messages "
        "SET classification_status = 'classified' "
        "WHERE classification_status = 'completed'"
    )
    op.execute(
        "UPDATE inbound_messages "
        "SET classification_status = 'pending' "
        "WHERE classification_status = 'skipped'"
    )
    op.execute(
        "UPDATE inbound_messages "
        "SET classified_at = updated_at "
        "WHERE classification_status = 'classified' AND classified_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("inbound_messages", "classified_at")
    op.drop_column("inbound_messages", "classification_model")
    op.drop_column("inbound_messages", "classification_role")
    op.drop_column("inbound_messages", "classification_error")
