"""Yarn lot traceability, remaining quantity, and opening balances.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter yarn_lot to make receipt_id nullable, add remaining_g and check constraints
    with op.batch_alter_table('yarn_lot', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('remaining_g', sa.BigInteger(), nullable=False, server_default='0')
        )
        batch_op.alter_column(
            'receipt_id',
            existing_type=sa.Integer(),
            nullable=True
        )
        batch_op.create_check_constraint(
            'ck_yarn_lot_remaining_non_negative',
            'remaining_g >= 0'
        )
        batch_op.create_check_constraint(
            'ck_yarn_lot_qty_non_negative',
            'qty_g >= 0'
        )
        batch_op.create_check_constraint(
            'ck_yarn_lot_remaining_lte_qty',
            'remaining_g <= qty_g'
        )

    # 2. Backfill existing lots if any
    op.execute(sa.text("""
        UPDATE yarn_lot
        SET remaining_g = qty_g
        WHERE remaining_g = 0;
    """))

    # 3. Create one opening-balance batch per yarn item for existing stock in RAW
    op.execute(sa.text("""
        INSERT INTO yarn_lot (receipt_id, item_id, lot_number, qty_g, remaining_g, is_active, created_at)
        SELECT 
            NULL, 
            sl.item_id, 
            'LOT-OPENING-' || i.sku, 
            sl.qty_g, 
            sl.qty_g, 
            1, 
            CURRENT_TIMESTAMP
        FROM stock_level sl
        JOIN item i ON sl.item_id = i.id
        JOIN location loc ON sl.location_id = loc.id
        WHERE loc.code = 'RAW' 
          AND i.item_type = 'yarn' 
          AND sl.qty_g > 0
          AND NOT EXISTS (
              SELECT 1 FROM yarn_lot yl WHERE yl.item_id = sl.item_id AND yl.lot_number = 'LOT-OPENING-' || i.sku
          );
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM yarn_lot WHERE receipt_id IS NULL;"))
    with op.batch_alter_table('yarn_lot', schema=None) as batch_op:
        batch_op.drop_constraint('ck_yarn_lot_remaining_lte_qty', type_='check')
        batch_op.drop_constraint('ck_yarn_lot_qty_non_negative', type_='check')
        batch_op.drop_constraint('ck_yarn_lot_remaining_non_negative', type_='check')
        batch_op.alter_column(
            'receipt_id',
            existing_type=sa.Integer(),
            nullable=False
        )
        batch_op.drop_column('remaining_g')
