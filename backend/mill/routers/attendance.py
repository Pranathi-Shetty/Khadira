"""Attendance and wage runs router."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import (
    AttendanceEntry, AttendanceStatus, WageBasis, WageRun,
    WageRunLine, WageRunStatus, Worker, User,
)
from mill.services import attendance as att_svc
from mill.services import wages as wage_svc

router = APIRouter(prefix="/api/attendance", tags=["attendance"])
wages_router = APIRouter(prefix="/api/wages", tags=["wages"])


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class WorkerIn(BaseModel):
    employee_id: str
    full_name: str
    wage_basis: WageBasis
    hourly_rate_paise: int = 0
    piece_rate_paise: int = 0
    phone: Optional[str] = None


@router.get("/workers")
def list_workers(db: Session = Depends(get_db), _=Depends(can("attendance.read"))):
    workers = db.query(Worker).filter(Worker.is_active == True).all()
    return [
        {
            "id": w.id, "employee_id": w.employee_id, "full_name": w.full_name,
            "wage_basis": w.wage_basis,
            "hourly_rate_paise": w.hourly_rate_paise,
            "piece_rate_paise": w.piece_rate_paise,
            "phone": w.phone,
        }
        for w in workers
    ]


@router.post("/workers")
def create_worker(
    body: WorkerIn,
    db: Session = Depends(get_db),
    _=Depends(can("attendance.write")),
):
    worker = Worker(**body.model_dump())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return {"id": worker.id, "employee_id": worker.employee_id}


# ---------------------------------------------------------------------------
# Attendance entries
# ---------------------------------------------------------------------------

class AttendanceIn(BaseModel):
    worker_id: int
    work_date: date
    shift: str
    hours_worked: Optional[int] = None    # minutes
    pieces_produced: Optional[int] = None
    order_id: Optional[int] = None
    run_id: Optional[int] = None
    notes: Optional[str] = None


@router.get("/entries")
def list_entries(
    worker_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(can("attendance.read")),
):
    q = db.query(AttendanceEntry)
    if worker_id:
        q = q.filter(AttendanceEntry.worker_id == worker_id)
    if from_date:
        q = q.filter(AttendanceEntry.work_date >= from_date)
    if to_date:
        q = q.filter(AttendanceEntry.work_date <= to_date)
    if status:
        q = q.filter(AttendanceEntry.status == status)
    entries = q.order_by(AttendanceEntry.work_date.desc()).all()
    return [
        {
            "id": e.id, "worker_id": e.worker_id,
            "worker_name": e.worker.full_name,
            "work_date": e.work_date, "shift": e.shift,
            "hours_worked": e.hours_worked, "pieces_produced": e.pieces_produced,
            "status": e.status, "notes": e.notes,
        }
        for e in entries
    ]


@router.post("/entries")
def create_entry(
    body: AttendanceIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("attendance.write")),
):
    try:
        entry = att_svc.create_entry(db, **body.model_dump(), created_by=user.id)
        db.commit()
        return {"id": entry.id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/entries/{entry_id}/approve")
def approve_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(can("attendance.approve")),
):
    try:
        entry = att_svc.approve_entry(db, entry_id, user.id)
        db.commit()
        return {"ok": True, "status": entry.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/entries/{entry_id}/void")
def void_entry(
    entry_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(can("attendance.approve")),
):
    reason = body.get("reason", "")
    if not reason:
        raise HTTPException(400, "Void reason is required")
    try:
        entry = att_svc.void_entry(db, entry_id, reason, user.id)
        db.commit()
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Wage runs
# ---------------------------------------------------------------------------

class WageRunIn(BaseModel):
    period_start: date
    period_end: date


@wages_router.post("/calculate")
def calculate_wage_run(
    body: WageRunIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("wages.write")),
):
    try:
        run = wage_svc.calculate_wage_run(
            db,
            period_start=body.period_start,
            period_end=body.period_end,
            created_by=user.id,
        )
        db.commit()
        return {"id": run.id, "status": run.status, "line_count": len(run.lines)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@wages_router.get("/")
def list_wage_runs(db: Session = Depends(get_db), _=Depends(can("wages.read"))):
    runs = db.query(WageRun).order_by(WageRun.period_start.desc()).all()
    return [
        {
            "id": r.id, "period_start": r.period_start, "period_end": r.period_end,
            "status": r.status, "calculated_at": r.calculated_at,
            "line_count": len(r.lines),
            "total_wage_paise": sum(l.net_wage_paise for l in r.lines),
        }
        for r in runs
    ]


@wages_router.get("/{run_id}")
def get_wage_run(run_id: int, db: Session = Depends(get_db), _=Depends(can("wages.read"))):
    run = db.query(WageRun).filter(WageRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Wage run not found")
    return {
        "id": run.id,
        "period_start": run.period_start,
        "period_end": run.period_end,
        "status": run.status,
        "calculated_at": run.calculated_at,
        "lines": [
            {
                "worker_id": l.worker_id,
                "worker_name": l.worker.full_name,
                "wage_basis": l.worker.wage_basis,
                "total_hours_minutes": l.total_hours_minutes,
                "total_pieces": l.total_pieces,
                "applied_rate_paise": l.applied_rate_paise,
                "base_wage_paise": l.base_wage_paise,
                "adjustment_paise": l.adjustment_paise,
                "net_wage_paise": l.net_wage_paise,
                "note": l.note,
            }
            for l in run.lines
        ],
    }


@wages_router.post("/{run_id}/finalise")
def finalise_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(can("wages.finalise")),
):
    try:
        run = wage_svc.finalise_wage_run(db, run_id, user.id)
        db.commit()
        return {"ok": True, "status": run.status}
    except ValueError as e:
        raise HTTPException(400, str(e))
