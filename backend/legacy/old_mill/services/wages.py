"""Monthly wage calculation and finalisation service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from mill.models import (
    AttendanceEntry, AttendanceStatus, WageBasis, WageRun,
    WageRunLine, WageRunStatus, Worker,
)


def calculate_wage_run(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    created_by: int,
) -> WageRun:
    """
    Create (or replace draft) a wage run for the period.
    Finalised runs are immutable — use adjustment entries instead.
    """
    existing = db.query(WageRun).filter(
        WageRun.period_start == period_start,
        WageRun.period_end == period_end,
    ).first()

    if existing and existing.status == WageRunStatus.finalised:
        raise ValueError("Wage run for this period is already finalised. Use an adjustment.")

    # Delete existing draft lines
    if existing:
        db.query(WageRunLine).filter(WageRunLine.wage_run_id == existing.id).delete()
        run = existing
    else:
        run = WageRun(
            period_start=period_start,
            period_end=period_end,
            created_by=created_by,
        )
        db.add(run)
        db.flush()

    # Gather approved entries for the period
    entries = (
        db.query(AttendanceEntry)
        .filter(
            AttendanceEntry.work_date >= period_start,
            AttendanceEntry.work_date <= period_end,
            AttendanceEntry.status == AttendanceStatus.approved,
        )
        .all()
    )

    # Group by worker
    from collections import defaultdict
    worker_entries: dict[int, list[AttendanceEntry]] = defaultdict(list)
    for e in entries:
        worker_entries[e.worker_id].append(e)

    workers = {w.id: w for w in db.query(Worker).filter(Worker.id.in_(worker_entries.keys())).all()}

    for worker_id, w_entries in worker_entries.items():
        worker = workers[worker_id]
        total_minutes = sum(e.hours_worked or 0 for e in w_entries)
        total_pieces = sum(e.pieces_produced or 0 for e in w_entries)

        if worker.wage_basis == WageBasis.hourly:
            # rate is paise/hour; time stored in minutes
            base_wage = (total_minutes * worker.hourly_rate_paise) // 60
            applied_rate = worker.hourly_rate_paise
        else:
            base_wage = total_pieces * worker.piece_rate_paise
            applied_rate = worker.piece_rate_paise

        line = WageRunLine(
            wage_run_id=run.id,
            worker_id=worker_id,
            total_hours_minutes=total_minutes,
            total_pieces=total_pieces,
            applied_rate_paise=applied_rate,
            base_wage_paise=base_wage,
            adjustment_paise=0,
            net_wage_paise=base_wage,
        )
        db.add(line)

    run.calculated_at = datetime.utcnow()
    run.status = WageRunStatus.draft
    return run


def finalise_wage_run(db: Session, run_id: int, finalised_by: int) -> WageRun:
    run = db.query(WageRun).filter(WageRun.id == run_id).first()
    if run is None:
        raise ValueError("Wage run not found")
    if run.status == WageRunStatus.finalised:
        raise ValueError("Already finalised")
    run.status = WageRunStatus.finalised
    run.finalised_by = finalised_by
    run.finalised_at = datetime.utcnow()
    return run
