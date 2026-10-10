"""Finance models: invoices, lines, payments."""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .partners import Buyer, Supplier


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)  # sale | purchase
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyer.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"))
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|sent|paid|cancelled
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    buyer: Mapped[Buyer | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[float] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_pct: Mapped[float] = mapped_column(Integer, default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"), nullable=False)
    paid_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    method: Mapped[str | None] = mapped_column(String(40))  # cash|upi|neft|cheque
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
