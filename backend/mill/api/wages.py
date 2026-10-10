"""Attendance-backed wage runs for the active ERP database."""

from datetime import date, datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..models import AttendanceEntry, Worker, WageRun, WageRunLine
from ..services.common import DomainError, audit
from .deps import Db, can

router = APIRouter(prefix="/api/wages", tags=["wages"])


class WageRunIn(BaseModel):
    period_start: date
    period_end: date


def _out(db, run: WageRun) -> dict:
    lines = db.scalars(select(WageRunLine).where(WageRunLine.wage_run_id == run.id)).all()
    return {"id": run.id, "period_start": run.period_start.isoformat(),
            "period_end": run.period_end.isoformat(), "status": run.status,
            "total_wage_paise": sum(line.net_wage_paise for line in lines),
            "lines": [{"worker_id": line.worker_id,
                       "worker_name": (db.get(Worker, line.worker_id).full_name if db.get(Worker, line.worker_id) else "Unknown"),
                       "total_hours_minutes": line.total_hours_minutes,
                       "total_pieces": line.total_pieces,
                       "applied_rate_paise": line.applied_rate_paise,
                       "net_wage_paise": line.net_wage_paise} for line in lines],
            "created_at": run.created_at.isoformat(),
            "finalised_at": run.finalised_at.isoformat() if run.finalised_at else None}


@router.get("")
def list_wage_runs(db: Db, _: can("wages.read")) -> list[dict]:
    return [_out(db, run) for run in db.scalars(select(WageRun).order_by(WageRun.id.desc())).all()]


@router.post("/calculate", status_code=201)
def calculate_wages(body: WageRunIn, db: Db, user: can("wages.write")) -> dict:
    if body.period_end < body.period_start:
        raise DomainError("period_end must be on or after period_start.")
    run = db.scalar(select(WageRun).where(WageRun.period_start == body.period_start,
                                          WageRun.period_end == body.period_end))
    if run and run.status == "finalised":
        raise DomainError("This wage period is finalised and cannot be recalculated.", 409)
    if run is None:
        run = WageRun(period_start=body.period_start, period_end=body.period_end,
                      created_by_id=user.id, status="draft")
        db.add(run)
        db.flush()
    else:
        for line in db.scalars(select(WageRunLine).where(WageRunLine.wage_run_id == run.id)).all():
            db.delete(line)
    entries = db.scalars(select(AttendanceEntry).where(
        AttendanceEntry.work_date.between(body.period_start, body.period_end),
        AttendanceEntry.status == "approved")).all()
    totals: dict[int, dict[str, int]] = {}
    for entry in entries:
        totals.setdefault(entry.worker_id, {"minutes": 0, "pieces": 0})
        totals[entry.worker_id]["minutes"] += entry.hours_worked or 0
        totals[entry.worker_id]["pieces"] += entry.pieces_produced or 0
    for worker_id, total in totals.items():
        worker = db.get(Worker, worker_id)
        if not worker or not worker.is_active:
            continue
        rate = worker.hourly_rate_paise if worker.wage_basis == "hourly" else worker.piece_rate_paise
        wage = (total["minutes"] * rate // 60 if worker.wage_basis == "hourly"
                else total["pieces"] * rate)
        db.add(WageRunLine(wage_run_id=run.id, worker_id=worker_id,
                           total_hours_minutes=total["minutes"], total_pieces=total["pieces"],
                           applied_rate_paise=rate, net_wage_paise=wage))
    audit(db, entity="WageRun", entity_id=run.id, action="calculate", user_id=user.id)
    db.commit()
    db.refresh(run)
    return _out(db, run)


@router.post("/{run_id}/finalise")
def finalise_wages(run_id: int, db: Db, user: can("wages.finalise")) -> dict:
    run = db.get(WageRun, run_id)
    if run is None:
        raise DomainError("Wage run not found.", 404)
    if run.status == "finalised":
        raise DomainError("Wage run is already finalised.", 409)
    run.status = "finalised"
    run.finalised_by_id = user.id
    run.finalised_at = datetime.now(timezone.utc)
    audit(db, entity="WageRun", entity_id=run.id, action="finalise", user_id=user.id)
    db.commit()
    db.refresh(run)
    return _out(db, run)
