"""Initial schema — items, partners, inventory, purchasing, orders, finance

Revision ID: 0001
Revises:
Create Date: 2026-10-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("user_account",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(120), unique=True, nullable=False),
        sa.Column("email", sa.String(200)),
        sa.Column("full_name", sa.String(200)),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="office"),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("user_session",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("location",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.create_table("item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String(60), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kg"),
        sa.Column("count_denier", sa.String(40)),
        sa.Column("gsm", sa.Integer),
        sa.Column("width_cm", sa.Integer),
        sa.Column("yarn_kg_per_meter", sa.Numeric(10, 4)),
        sa.Column("reorder_point_kg", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("stock_level",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id"), nullable=False),
        sa.Column("qty_g", sa.BigInteger, server_default="0"),
        sa.UniqueConstraint("item_id", "location_id"),
    )
    op.create_table("stock_move",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id"), nullable=False),
        sa.Column("delta_g", sa.BigInteger, nullable=False),
        sa.Column("ref", sa.String(100)),
        sa.Column("note", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_account.id")),
        sa.Column("entity", sa.String(60)),
        sa.Column("entity_id", sa.Integer),
        sa.Column("action", sa.String(60)),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("supplier",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_name", sa.String(150)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(200)),
        sa.Column("address", sa.Text),
        sa.Column("gstin", sa.String(20)),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("buyer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_name", sa.String(150)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(200)),
        sa.Column("address", sa.Text),
        sa.Column("gstin", sa.String(20)),
        sa.Column("credit_days", sa.Integer, server_default="30"),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("purchase_order",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ref", sa.String(60), unique=True, nullable=False),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("supplier.id"), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("expected_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("purchase_order_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("po_id", sa.Integer, sa.ForeignKey("purchase_order.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("qty_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("rate_per_kg_paise", sa.BigInteger, nullable=False),
        sa.Column("received_kg", sa.Numeric(12, 3), server_default="0"),
    )
    op.create_table("yarn_receipt",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("po_id", sa.Integer, sa.ForeignKey("purchase_order.id"), nullable=False),
        sa.Column("po_line_id", sa.Integer, sa.ForeignKey("purchase_order_line.id"), nullable=False),
        sa.Column("received_date", sa.Date, nullable=False),
        sa.Column("qty_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("vehicle_no", sa.String(30)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("yarn_lot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("receipt_id", sa.Integer, sa.ForeignKey("yarn_receipt.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("lot_number", sa.String(60), nullable=False),
        sa.Column("qty_g", sa.BigInteger, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("sale_order",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ref", sa.String(60), unique=True, nullable=False),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("buyer.id"), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("delivery_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("sale_order_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("sale_order.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("qty_meters", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate_per_meter_paise", sa.BigInteger, nullable=False),
    )
    op.create_table("invoice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ref", sa.String(60), unique=True, nullable=False),
        sa.Column("invoice_type", sa.String(20), nullable=False),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("buyer.id")),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("supplier.id")),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("invoice_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoice.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("unit_price_paise", sa.BigInteger, nullable=False),
        sa.Column("tax_pct", sa.Integer, server_default="0"),
    )
    op.create_table("payment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoice.id"), nullable=False),
        sa.Column("paid_date", sa.Date, nullable=False),
        sa.Column("amount_paise", sa.BigInteger, nullable=False),
        sa.Column("method", sa.String(40)),
        sa.Column("reference", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table("app_setting",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.Text),
    )


def downgrade() -> None:
    for t in ["payment", "invoice_line", "invoice", "sale_order_line", "sale_order",
              "yarn_lot", "yarn_receipt", "purchase_order_line", "purchase_order",
              "buyer", "supplier", "audit_log", "stock_move", "stock_level",
              "item", "location", "user_session", "user_account", "app_setting"]:
        op.drop_table(t)
