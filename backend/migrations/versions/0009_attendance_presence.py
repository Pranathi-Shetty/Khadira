"""Attendance presence tracking and singular table synchronization.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    # 1. Synchronize worker table if demo db only has plural workers
    if 'worker' not in tables and 'workers' in tables:
        op.create_table(
            'worker',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(40), nullable=False, unique=True),
            sa.Column('full_name', sa.String(160), nullable=False),
            sa.Column('department', sa.String(80), nullable=False, server_default='Production'),
            sa.Column('wage_basis', sa.String(20), nullable=False, server_default='hourly'),
            sa.Column('hourly_rate_paise', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('piece_rate_paise', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True)),
        )
        op.execute(
            "INSERT OR IGNORE INTO worker (id, code, full_name, department, wage_basis, hourly_rate_paise, piece_rate_paise, is_active, created_at) "
            "SELECT id, COALESCE(employee_id, 'WRK-' || id), full_name, 'Production', COALESCE(wage_basis, 'hourly'), COALESCE(hourly_rate_paise, 0), COALESCE(piece_rate_paise, 0), is_active, created_at FROM workers"
        )
        tables.add('worker')

    # 2. Add is_present to attendance_entry, or create attendance_entry from attendance_entries
    if 'attendance_entry' in tables:
        cols = [c['name'] for c in insp.get_columns('attendance_entry')]
        if 'is_present' not in cols:
            with op.batch_alter_table('attendance_entry', schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column('is_present', sa.Boolean(), nullable=False, server_default=sa.text('1'))
                )
    elif 'attendance_entries' in tables:
        op.create_table(
            'attendance_entry',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('worker_id', sa.Integer(), nullable=False),
            sa.Column('work_date', sa.Date(), nullable=False),
            sa.Column('shift', sa.String(30), nullable=False),
            sa.Column('hours_worked', sa.Integer()),
            sa.Column('pieces_produced', sa.Integer()),
            sa.Column('is_present', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('order_id', sa.Integer()),
            sa.Column('run_id', sa.Integer()),
            sa.Column('notes', sa.Text()),
            sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
            sa.Column('created_by_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('approved_by_id', sa.Integer()),
            sa.Column('approved_at', sa.DateTime(timezone=True)),
            sa.Column('created_at', sa.DateTime(timezone=True)),
        )
        op.execute(
            "INSERT OR IGNORE INTO attendance_entry (id, worker_id, work_date, shift, hours_worked, pieces_produced, is_present, status, created_by_id, created_at) "
            "SELECT id, worker_id, work_date, shift, hours_worked, pieces_produced, 1, status, COALESCE(created_by, 1), created_at FROM attendance_entries"
        )
        tables.add('attendance_entry')

    # 3. Synchronize wage_run if missing
    if 'wage_run' not in tables and 'wage_runs' in tables:
        op.create_table(
            'wage_run',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
            sa.Column('created_by_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('finalised_by_id', sa.Integer()),
            sa.Column('created_at', sa.DateTime(timezone=True)),
            sa.Column('finalised_at', sa.DateTime(timezone=True)),
        )
        op.execute(
            "INSERT OR IGNORE INTO wage_run (id, period_start, period_end, status, created_by_id, created_at) "
            "SELECT id, period_start, period_end, status, COALESCE(created_by, 1), created_at FROM wage_runs"
        )

    # 4. Synchronize order_cost if missing
    if 'order_cost' not in tables and 'order_costs' in tables:
        op.create_table(
            'order_cost',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('order_id', sa.Integer(), nullable=False, unique=True),
            sa.Column('yarn_used_g', sa.BigInteger()),
            sa.Column('material_cost_paise', sa.BigInteger()),
            sa.Column('allocated_wage_paise', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('overhead_paise', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('known_cost_paise', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('passed_metres', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('cost_per_passed_metre_paise', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('overhead_method', sa.String(30), nullable=False, server_default='per_metre'),
            sa.Column('calculated_at', sa.DateTime(timezone=True)),
        )
        op.execute(
            "INSERT OR IGNORE INTO order_cost (id, order_id, yarn_used_g, material_cost_paise, allocated_wage_paise, overhead_paise, known_cost_paise, passed_metres, cost_per_passed_metre_paise, calculated_at) "
            "SELECT id, order_id, 0, yarn_cost_paise, allocated_wage_paise, overhead_paise, total_cost_paise, passed_metres, cost_per_passed_metre_paise, calculated_at FROM order_costs"
        )


def downgrade() -> None:
    with op.batch_alter_table('attendance_entry', schema=None) as batch_op:
        batch_op.drop_column('is_present')
