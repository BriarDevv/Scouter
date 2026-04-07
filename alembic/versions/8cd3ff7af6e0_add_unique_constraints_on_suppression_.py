"""add unique constraints on suppression domain and phone

Revision ID: 8cd3ff7af6e0
Revises: b5a27898773e
Create Date: 2026-04-07 02:01:25.274288

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8cd3ff7af6e0'
down_revision: Union[str, None] = 'b5a27898773e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_suppression_list_domain', 'suppression_list', ['domain'])
    op.create_unique_constraint('uq_suppression_list_phone', 'suppression_list', ['phone'])


def downgrade() -> None:
    op.drop_constraint('uq_suppression_list_phone', 'suppression_list', type_='unique')
    op.drop_constraint('uq_suppression_list_domain', 'suppression_list', type_='unique')
