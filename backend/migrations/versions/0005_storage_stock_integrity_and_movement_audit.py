"""Storage-level stock integrity and movement audit fields.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add non-negative constraint on stock_level
    with op.batch_alter_table('stock_level', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_stock_level_qty_non_negative',
            'qty_g >= 0'
        )

    # 2. Add movement_type and user_id to stock_move with storage-level type and direction constraints
    # Historical audit note: user_id defaults to 1 (admin) for existing rows strictly because the historical actor is unrecorded.
    with op.batch_alter_table('stock_move', schema=None) as batch_op:
        batch_op.add_column(sa.Column('movement_type', sa.String(length=30), nullable=False, server_default='legacy'))
        batch_op.add_column(sa.Column('user_id', sa.Integer(), sa.ForeignKey('user_account.id', name='fk_stock_move_user_id'), nullable=False, server_default='1'))
        batch_op.create_check_constraint(
            'ck_stock_move_movement_type',
            "movement_type IN ('receipt', 'yarn_issue', 'yarn_return', 'fabric_in', 'fabric_out', 'opening_balance', 'adjustment', 'legacy')"
        )
        batch_op.create_check_constraint(
            'ck_stock_move_type_direction',
            "((movement_type = 'receipt' AND delta_g > 0) OR "
            "(movement_type = 'fabric_in' AND delta_g > 0) OR "
            "(movement_type = 'yarn_return' AND delta_g > 0) OR "
            "(movement_type = 'opening_balance' AND delta_g > 0) OR "
            "(movement_type = 'yarn_issue' AND delta_g < 0) OR "
            "(movement_type = 'fabric_out' AND delta_g < 0) OR "
            "(movement_type IN ('adjustment', 'legacy') AND delta_g != 0))"
        )

    # 3. Data migration: infer movement_type from existing ref and notes.
    # Opening balances receive a distinct type 'opening_balance'.
    # user_id is populated with 1 (admin) only because the actual actor is unknown on legacy rows.
    op.execute(sa.text("""
        UPDATE stock_move
        SET movement_type = CASE
            WHEN note LIKE '%Opening%' OR ref = 'INIT-STOCK' THEN 'opening_balance'
            WHEN ref LIKE 'PO-%' OR note LIKE '%Receipt%' THEN 'receipt'
            WHEN (ref LIKE 'RUN-%' OR note LIKE '%reconciliation return%') AND delta_g > 0 THEN 'yarn_return'
            WHEN ref LIKE 'RUN-%' OR note LIKE '%issue%' OR note LIKE '%consumed%' THEN 'yarn_issue'
            WHEN ref LIKE 'ROLL-%' OR note LIKE '%fabric_in%' OR note LIKE '%Passed QC%' THEN 'fabric_in'
            WHEN note LIKE '%fabric_out%' OR ref LIKE 'DISPATCH-%' THEN 'fabric_out'
            WHEN ref LIKE 'STOCKCOUNT-%' OR note LIKE '%variance%' OR note LIKE '%waste%' THEN 'adjustment'
            ELSE 'legacy'
        END,
        user_id = COALESCE(user_id, 1);
    """))


def downgrade() -> None:
    with op.batch_alter_table('stock_move', schema=None) as batch_op:
        batch_op.drop_constraint('ck_stock_move_type_direction', type_='check')
        batch_op.drop_constraint('ck_stock_move_movement_type', type_='check')
        batch_op.drop_constraint('fk_stock_move_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
        batch_op.drop_column('movement_type')

    with op.batch_alter_table('stock_level', schema=None) as batch_op:
        batch_op.drop_constraint('ck_stock_level_qty_non_negative', type_='check')
