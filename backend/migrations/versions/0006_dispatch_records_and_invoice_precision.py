"""Dispatch records, dispatch roll constraint, and invoice decimal precision.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create dispatch table
    op.create_table(
        'dispatch',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatch_number', sa.String(length=60), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('sale_order.id', name='fk_dispatch_order_id'), nullable=True),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('buyer.id', name='fk_dispatch_buyer_id'), nullable=True),
        sa.Column('dispatch_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='confirmed'),
        sa.Column('vehicle_no', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('user_account.id', name='fk_dispatch_created_by_id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispatch_number', name='uq_dispatch_number')
    )

    # 2. Create dispatch_roll table with unique constraint on roll_id (prevent double dispatch)
    op.create_table(
        'dispatch_roll',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatch_id', sa.Integer(), sa.ForeignKey('dispatch.id', ondelete='CASCADE', name='fk_dispatch_roll_dispatch_id'), nullable=False),
        sa.Column('roll_id', sa.Integer(), sa.ForeignKey('roll.id', name='fk_dispatch_roll_roll_id'), nullable=False),
        sa.Column('length_cm', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('roll_id', name='uq_dispatch_roll_unique')
    )

    # 3. Batch alter invoice: add order_id and dispatch_id foreign keys
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.add_column(sa.Column('order_id', sa.Integer(), sa.ForeignKey('sale_order.id', name='fk_invoice_order_id'), nullable=True))
        batch_op.add_column(sa.Column('dispatch_id', sa.Integer(), sa.ForeignKey('dispatch.id', name='fk_invoice_dispatch_id'), nullable=True))

    # 4. Batch alter invoice_line: alter qty to Numeric(12, 3) and tax_pct to Numeric(5, 2)
    with op.batch_alter_table('invoice_line', schema=None) as batch_op:
        batch_op.alter_column(
            'qty',
            existing_type=sa.Integer(),
            type_=sa.Numeric(precision=12, scale=3),
            existing_nullable=False
        )
        batch_op.alter_column(
            'tax_pct',
            existing_type=sa.Integer(),
            type_=sa.Numeric(precision=5, scale=2),
            existing_nullable=False,
            existing_server_default=sa.text('0')
        )


def downgrade() -> None:
    with op.batch_alter_table('invoice_line', schema=None) as batch_op:
        batch_op.alter_column(
            'tax_pct',
            existing_type=sa.Numeric(precision=5, scale=2),
            type_=sa.Integer(),
            existing_nullable=False
        )
        batch_op.alter_column(
            'qty',
            existing_type=sa.Numeric(precision=12, scale=3),
            type_=sa.Integer(),
            existing_nullable=False
        )

    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.drop_column('dispatch_id')
        batch_op.drop_column('order_id')

    op.drop_table('dispatch_roll')
    op.drop_table('dispatch')
