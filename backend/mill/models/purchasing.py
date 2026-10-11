"""Purchasing models: PO, PO lines, yarn receipts and lots."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .core import Item
from .partners import Supplier


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("supplier.id"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|confirmed|received|cancelled
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    supplier: Mapped[Supplier] = relationship()
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="po", cascade="all, delete-orphan")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_order.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    qty_kg: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    rate_per_kg_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)  # INR paise
    received_kg: Mapped[float] = mapped_column(Numeric(12, 3), default=0)

    po: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship()


class YarnReceipt(Base):
    __tablename__ = "yarn_receipt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_order.id"), nullable=False)
    po_line_id: Mapped[int] = mapped_column(ForeignKey("purchase_order_line.id"), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    qty_kg: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    vehicle_no: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    po: Mapped[PurchaseOrder] = relationship()
    po_line: Mapped[PurchaseOrderLine] = relationship()


class YarnLot(Base):
    __tablename__ = "yarn_lot"
    __table_args__ = (
        CheckConstraint("remaining_g >= 0", name="ck_yarn_lot_remaining_non_negative"),
        CheckConstraint("qty_g >= 0", name="ck_yarn_lot_qty_non_negative"),
        CheckConstraint("remaining_g <= qty_g", name="ck_yarn_lot_remaining_lte_qty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("yarn_receipt.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(60), nullable=False)
    qty_g: Mapped[int] = mapped_column(BigInteger, nullable=False)  # grams
    remaining_g: Mapped[int] = mapped_column(BigInteger, nullable=False)  # grams
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    receipt: Mapped[YarnReceipt | None] = relationship()
    item: Mapped[Item] = relationship()
    run_materials: Mapped[list["RunMaterial"]] = relationship(back_populates="lot")
