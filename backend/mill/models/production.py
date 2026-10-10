"""Production models: machines, runs, rolls and roll events."""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .core import Item
from .orders import Order


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Ordered stages every machine type goes through
MACHINE_STAGES: dict[str, list[str]] = {
    "spinning":  ["loading", "spinning", "doffing"],
    "weaving":   ["warping", "weaving", "inspection"],
    "dyeing":    ["prep", "dyeing", "finishing"],
}


class Machine(Base):
    __tablename__ = "machine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(30), nullable=False)  # spinning|weaving|dyeing
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    runs: Mapped[list["ProductionRun"]] = relationship(back_populates="machine")


class ProductionRun(Base):
    __tablename__ = "production_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machine.id"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sale_order.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|cancelled
    yarn_used_g: Mapped[int] = mapped_column(BigInteger, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    machine: Mapped[Machine] = relationship(back_populates="runs")
    order: Mapped[Order | None] = relationship()
    item: Mapped[Item] = relationship()
    rolls: Mapped[list["Roll"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Roll(Base):
    __tablename__ = "roll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roll_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    run_id: Mapped[int] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    length_cm: Mapped[int] = mapped_column(Integer, nullable=False)  # centimetres for precision
    weight_g: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="awaiting_qc")
    # awaiting_qc | passed | failed | held | in_store | dispatched
    qc_grade: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[ProductionRun] = relationship(back_populates="rolls")
    item: Mapped[Item] = relationship()
    events: Mapped[list["RollEvent"]] = relationship(back_populates="roll", cascade="all, delete-orphan")


class RollEvent(Base):
    __tablename__ = "roll_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roll_id: Mapped[int] = mapped_column(ForeignKey("roll.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    roll: Mapped[Roll] = relationship(back_populates="events")
