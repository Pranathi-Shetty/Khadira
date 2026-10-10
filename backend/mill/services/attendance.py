"""Attendance CRUD and approval service."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from mill.models import AttendanceEntry, AttendanceStatus, WageBasis, Worker


def create_entry(
    db: Session,
    *,
    worker_id: int,
    work_date: date,
    shift: str,
    hours_worked: Optional[int] = None,    # minutes
    pieces_produced: Optional[int] = None,
    order_id: Optional[int] = None,
    run_id: Optional[int] = None,
    notes: Optional[str] = None,
    created_by: int,
) -> AttendanceEntry:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise ValueError("Worker not found")

    # Validate basis
    if worker.wage_basis == WageBasis.hourly:
        if hours_worked is None or hours_worked <= 0:
            raise ValueError("hours_worked must be positive for hourly workers")
    elif worker.wage_basis == WageBasis.piece_rate:
        if pieces_produced is None or pieces_produced <= 0:
            raise ValueError("pieces_produced must be positive for piece-rate workers")

    # Check for duplicate shift entry
    existing = db.query(AttendanceEntry).filter(
        AttendanceEntry.worker_id == worker_id,
        AttendanceEntry.work_date == work_date,
        AttendanceEntry.shift == shift,
        AttendanceEntry.status != AttendanceStatus.voided,
    ).first()
    if existing:
        raise ValueError(f"Attendance already recorded for worker {worker_id} on {work_date} shift {shift}")

    entry = AttendanceEntry(
        worker_id=worker_id,
        work_date=work_date,
        shift=shift,
        hours_worked=hours_worked,
        pieces_produced=pieces_produced,
        order_id=order_id,
        run_id=run_id,
        notes=notes,
        created_by=created_by,
        status=AttendanceStatus.draft,
    )
    db.add(entry)
    db.flush()
    return entry


def approve_entry(db: Session, entry_id: int, approved_by: int) -> AttendanceEntry:
    from datetime import datetime
    entry = db.query(AttendanceEntry).filter(AttendanceEntry.id == entry_id).first()
    if entry is None:
        raise ValueError("Attendance entry not found")
    if entry.status != AttendanceStatus.draft:
        raise ValueError(f"Cannot approve entry in status {entry.status}")
    entry.status = AttendanceStatus.approved
    entry.approved_by = approved_by
    entry.approved_at = datetime.utcnow()
    return entry


def void_entry(db: Session, entry_id: int, reason: str, voided_by: int) -> AttendanceEntry:
    entry = db.query(AttendanceEntry).filter(AttendanceEntry.id == entry_id).first()
    if entry is None:
        raise ValueError("Attendance entry not found")
    if entry.status == AttendanceStatus.voided:
        raise ValueError("Entry already voided")
    entry.status = AttendanceStatus.voided
    entry.void_reason = reason
    return entry
