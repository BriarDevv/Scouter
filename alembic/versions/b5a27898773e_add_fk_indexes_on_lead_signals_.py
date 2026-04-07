"""add FK indexes on lead_signals, artifacts, commercial_briefs

Revision ID: b5a27898773e
Revises: 694f94aae1c8
Create Date: 2026-04-07 01:43:51.105280

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b5a27898773e'
down_revision: Union[str, None] = '694f94aae1c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_artifacts_lead_id', 'artifacts', ['lead_id'], unique=False)
    op.create_index('ix_commercial_briefs_research_report_id', 'commercial_briefs', ['research_report_id'], unique=False)
    op.create_index('ix_lead_signals_lead_id', 'lead_signals', ['lead_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_lead_signals_lead_id', table_name='lead_signals')
    op.drop_index('ix_commercial_briefs_research_report_id', table_name='commercial_briefs')
    op.drop_index('ix_artifacts_lead_id', table_name='artifacts')
