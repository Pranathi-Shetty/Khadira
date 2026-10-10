"""Add active attendance, wage-run and order-costing tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("department", sa.String(80), nullable=False, server_default="Production"),
        sa.Column("wage_basis", sa.String(20), nullable=False, server_default="hourly"),
        sa.Column("hourly_rate_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("piece_rate_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "attendance_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.Integer(), sa.ForeignKey("worker.id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(30), nullable=False),
        sa.Column("hours_worked", sa.Integer()),
        sa.Column("pieces_produced", sa.Integer()),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("sale_order.id")),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("production_run.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("user_account.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("worker_id", "work_date", "shift", name="uq_attendance_worker_date_shift"),
    )
    op.create_table(
        "wage_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("finalised_by_id", sa.Integer(), sa.ForeignKey("user_account.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("finalised_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("period_start", "period_end", name="uq_wage_period"),
    )
    op.create_table(
        "wage_run_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wage_run_id", sa.Integer(), sa.ForeignKey("wage_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worker_id", sa.Integer(), sa.ForeignKey("worker.id"), nullable=False),
        sa.Column("total_hours_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_pieces", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applied_rate_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_wage_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("wage_run_id", "worker_id", name="uq_wage_worker"),
    )
    op.create_table(
        "order_cost",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("sale_order.id"), nullable=False, unique=True),
        sa.Column("yarn_used_g", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("material_cost_paise", sa.Integer()),
        sa.Column("allocated_wage_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overhead_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("known_cost_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_metres", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("order_cost")
    op.drop_table("wage_run_line")
    op.drop_table("wage_run")
    op.drop_table("attendance_entry")
    op.drop_table("worker")
