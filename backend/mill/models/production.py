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
    materials: Mapped[list["RunMaterial"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    reconciliation: Mapped["RunReconciliation | None"] = relationship(back_populates="run", uselist=False, cascade="all, delete-orphan")


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


class RunMaterial(Base):
    __tablename__ = "run_material"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("production_run.id"), nullable=False)
    lot_id: Mapped[int] = mapped_column(ForeignKey("yarn_lot.id"), nullable=False)
    stock_move_id: Mapped[int | None] = mapped_column(ForeignKey("stock_move.id"))
    issued_g: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped["ProductionRun"] = relationship(back_populates="materials")


class RunReconciliation(Base):
    __tablename__ = "run_reconciliation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("production_run.id"), unique=True, nullable=False)
    
    # Material side (yarn)
    planned_g: Mapped[int] = mapped_column(BigInteger, default=0)
    issued_g: Mapped[int] = mapped_column(BigInteger, default=0)
    consumed_g: Mapped[int] = mapped_column(BigInteger, default=0)
    returned_g: Mapped[int] = mapped_column(BigInteger, default=0)
    process_waste_g: Mapped[int] = mapped_column(BigInteger, default=0)
    
    # Output side (fabric)
    usable_output_cm: Mapped[int] = mapped_column(BigInteger, default=0)
    qc_rejected_cm: Mapped[int] = mapped_column(BigInteger, default=0)
    
    status: Mapped[str] = mapped_column(String(20), default="draft") # draft | finalized
    reason: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped["ProductionRun"] = relationship(back_populates="reconciliation")


class MachineDowntime(Base):
    __tablename__ = "machine_downtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machine.id"), nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("production_run.id"))
    reason: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. maintenance, breakdown, cleaning, material_shortage
    description: Mapped[str | None] = mapped_column(Text)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    
    machine: Mapped[Machine] = relationship()
    run: Mapped[ProductionRun | None] = relationship()


class RollDefect(Base):
    __tablename__ = "roll_defect"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roll_id: Mapped[int] = mapped_column(ForeignKey("roll.id"), nullable=False)
    defect_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. stain, hole, snag, yarn_break
    severity: Mapped[str] = mapped_column(String(20), default="minor") # minor, major, critical
    location_m: Mapped[int | None] = mapped_column(Integer) # approximate position in meters from start
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))

    roll: Mapped[Roll] = relationship()
