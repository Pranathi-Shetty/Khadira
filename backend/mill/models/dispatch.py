"""Dispatch models: dispatches and dispatched rolls."""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Dispatch(Base):
    __tablename__ = "dispatch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispatch_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sale_order.id"))
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyer.id"))
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    vehicle_no: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["Order | None"] = relationship()
    buyer: Mapped["Buyer | None"] = relationship()
    created_by: Mapped["User"] = relationship()
    rolls: Mapped[list["DispatchRoll"]] = relationship(back_populates="dispatch", cascade="all, delete-orphan")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="dispatch", uselist=False)


class DispatchRoll(Base):
    __tablename__ = "dispatch_roll"
    __table_args__ = (
        UniqueConstraint("roll_id", name="uq_dispatch_roll_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatch.id", ondelete="CASCADE"), nullable=False)
    roll_id: Mapped[int] = mapped_column(ForeignKey("roll.id"), nullable=False, unique=True)
    length_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    dispatch: Mapped[Dispatch] = relationship(back_populates="rolls")
    roll: Mapped["Roll"] = relationship()
