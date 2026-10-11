"""Workforce, attendance, and payroll records for the active ERP database."""

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Worker(Base):
    __tablename__ = "worker"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str] = mapped_column(String(80), default="Production")
    wage_basis: Mapped[str] = mapped_column(String(20), default="hourly")  # hourly|piece_rate
    hourly_rate_paise: Mapped[int] = mapped_column(Integer, default=0)
    piece_rate_paise: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AttendanceEntry(Base):
    __tablename__ = "attendance_entry"
    __table_args__ = (UniqueConstraint("worker_id", "work_date", "shift", name="uq_attendance_worker_date_shift"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("worker.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str] = mapped_column(String(30), nullable=False)
    # NOTE: Stored in MINUTES (1..1440, up to 24h). Named hours_worked in SQLite schema for compatibility.
    hours_worked: Mapped[int | None] = mapped_column(Integer)
    pieces_produced: Mapped[int | None] = mapped_column(Integer)
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sale_order.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("production_run.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|approved|voided
    created_by_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    @property
    def minutes_worked(self) -> int | None:
        """Alias for hours_worked reflecting true unit (minutes)."""
        return self.hours_worked

    @minutes_worked.setter
    def minutes_worked(self, val: int | None) -> None:
        self.hours_worked = val


class WageRun(Base):
    __tablename__ = "wage_run"
    __table_args__ = (UniqueConstraint("period_start", "period_end", name="uq_wage_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|finalised
    created_by_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    finalised_by_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WageRunLine(Base):
    __tablename__ = "wage_run_line"
    __table_args__ = (UniqueConstraint("wage_run_id", "worker_id", name="uq_wage_worker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wage_run_id: Mapped[int] = mapped_column(ForeignKey("wage_run.id", ondelete="CASCADE"), nullable=False)
    worker_id: Mapped[int] = mapped_column(ForeignKey("worker.id"), nullable=False)
    total_hours_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_pieces: Mapped[int] = mapped_column(Integer, default=0)
    applied_rate_paise: Mapped[int] = mapped_column(Integer, default=0)
    net_wage_paise: Mapped[int] = mapped_column(Integer, default=0)
