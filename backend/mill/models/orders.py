"""Sales order models."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .core import Item
from .partners import Buyer


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "sale_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyer.id"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[date | None] = mapped_column(Date)
    tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5.00"))
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft|confirmed|in_production|production_complete|delivered|cancelled
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    buyer: Mapped[Buyer] = relationship()
    lines: Mapped[list["OrderLine"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base):
    __tablename__ = "sale_order_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sale_order.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    qty_meters: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rate_per_meter_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    order: Mapped[Order] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship()
