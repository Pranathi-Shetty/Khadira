"""Production machines, runs, roll events, and QC inspections

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("machine",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("machine_type", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("production_run",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("machine_id", sa.Integer, sa.ForeignKey("machine.id"), nullable=False),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("sale_order.id")),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("current_stage", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("yarn_used_g", sa.BigInteger, server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table("roll",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("roll_number", sa.String(40), unique=True, nullable=False),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("production_run.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("length_cm", sa.Integer, nullable=False),
        sa.Column("weight_g", sa.Integer),
        sa.Column("status", sa.String(20), server_default="awaiting_qc"),
        sa.Column("qc_grade", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("roll_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("roll_id", sa.Integer, sa.ForeignKey("roll.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("note", sa.String(200)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("user_account.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("roll_event")
    op.drop_table("roll")
    op.drop_table("production_run")
    op.drop_table("machine")
