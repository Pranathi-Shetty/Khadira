"""Order tolerance percentage and expanded status.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sale_order', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('tolerance_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='5.00')
        )
        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
            existing_server_default='draft'
        )


def downgrade() -> None:
    with op.batch_alter_table('sale_order', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=30),
            type_=sa.String(length=20),
            existing_nullable=False,
            existing_server_default='draft'
        )
        batch_op.drop_column('tolerance_pct')
