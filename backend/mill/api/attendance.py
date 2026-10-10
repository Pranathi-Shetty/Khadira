"""Attendance and worker endpoints using the active auth/database stack."""

from datetime import date, datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import AttendanceEntry, Worker
from ..services.common import DomainError, audit
from .deps import Db, can

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class WorkerIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=160)
    department: str = "Production"
    wage_basis: str = "hourly"
    hourly_rate_paise: int = Field(default=0, ge=0)
    piece_rate_paise: int = Field(default=0, ge=0)


class AttendanceIn(BaseModel):
    worker_id: int
    work_date: date
    shift: str = Field(min_length=1, max_length=30)
    hours_worked: int | None = Field(default=None, gt=0, le=1440)  # minutes
    pieces_produced: int | None = Field(default=None, ge=0)
    order_id: int | None = None
    run_id: int | None = None
    notes: str | None = Field(default=None, max_length=1000)


def _worker_out(w: Worker) -> dict:
    return {"id": w.id, "code": w.code, "full_name": w.full_name,
            "department": w.department, "wage_basis": w.wage_basis,
            "is_active": w.is_active}


def _entry_out(e: AttendanceEntry, worker: Worker | None = None) -> dict:
    return {"id": e.id, "worker_id": e.worker_id,
            "worker_name": worker.full_name if worker else None,
            "work_date": e.work_date.isoformat(), "shift": e.shift,
            "hours_worked": e.hours_worked, "pieces_produced": e.pieces_produced,
            "order_id": e.order_id, "run_id": e.run_id, "notes": e.notes,
            "status": e.status, "created_by_id": e.created_by_id,
            "approved_by_id": e.approved_by_id,
            "approved_at": e.approved_at.isoformat() if e.approved_at else None}


@router.get("/workers")
def list_workers(db: Db, _: can("attendance.read")) -> list[dict]:
    workers = db.scalars(select(Worker).where(Worker.is_active.is_(True)).order_by(Worker.full_name)).all()
    return [_worker_out(w) for w in workers]


@router.post("/workers", status_code=201)
def create_worker(body: WorkerIn, db: Db, user: can("workers.write")) -> dict:
    if body.wage_basis not in {"hourly", "piece_rate"}:
        raise DomainError("wage_basis must be hourly or piece_rate.")
    if db.scalar(select(Worker).where(Worker.code == body.code.strip())):
        raise DomainError("Worker code already exists.", 409)
    worker = Worker(code=body.code.strip(), full_name=body.full_name.strip(),
                    department=body.department.strip(), wage_basis=body.wage_basis,
                    hourly_rate_paise=body.hourly_rate_paise,
                    piece_rate_paise=body.piece_rate_paise)
    db.add(worker)
    db.flush()
    audit(db, entity="Worker", entity_id=worker.id, action="create", user_id=user.id)
    db.commit()
    db.refresh(worker)
    return _worker_out(worker)


@router.get("")
def list_attendance(db: Db, _: can("attendance.read"),
                    start: date | None = None, end: date | None = None,
                    status: str | None = None) -> list[dict]:
    stmt = select(AttendanceEntry, Worker).join(Worker, Worker.id == AttendanceEntry.worker_id)
    if start:
        stmt = stmt.where(AttendanceEntry.work_date >= start)
    if end:
        stmt = stmt.where(AttendanceEntry.work_date <= end)
    if status:
        stmt = stmt.where(AttendanceEntry.status == status)
    return [_entry_out(entry, worker) for entry, worker in db.execute(
        stmt.order_by(AttendanceEntry.work_date.desc(), AttendanceEntry.id.desc())).all()]


@router.post("", status_code=201)
def record_attendance(body: AttendanceIn, db: Db, user: can("attendance.write")) -> dict:
    worker = db.get(Worker, body.worker_id)
    if worker is None or not worker.is_active:
        raise DomainError("Active worker not found.", 404)
    if worker.wage_basis == "hourly" and not body.hours_worked:
        raise DomainError("hours_worked is required for hourly workers.")
    if worker.wage_basis == "piece_rate" and body.pieces_produced is None:
        raise DomainError("pieces_produced is required for piece-rate workers.")
    duplicate = db.scalar(select(AttendanceEntry).where(
        AttendanceEntry.worker_id == body.worker_id,
        AttendanceEntry.work_date == body.work_date,
        AttendanceEntry.shift == body.shift,
        AttendanceEntry.status != "voided"))
    if duplicate:
        raise DomainError("Attendance already exists for this worker, date, and shift.", 409)
    entry = AttendanceEntry(**body.model_dump(), created_by_id=user.id, status="draft")
    db.add(entry)
    db.flush()
    audit(db, entity="AttendanceEntry", entity_id=entry.id, action="record", user_id=user.id)
    db.commit()
    db.refresh(entry)
    return _entry_out(entry, worker)


@router.post("/{entry_id}/approve")
def approve_attendance(entry_id: int, db: Db, user: can("attendance.approve")) -> dict:
    entry = db.get(AttendanceEntry, entry_id)
    if entry is None:
        raise DomainError("Attendance entry not found.", 404)
    if entry.status != "draft":
        raise DomainError("Only draft attendance can be approved.")
    entry.status = "approved"
    entry.approved_by_id = user.id
    entry.approved_at = datetime.now(timezone.utc)
    audit(db, entity="AttendanceEntry", entity_id=entry.id, action="approve", user_id=user.id)
    db.commit()
    db.refresh(entry)
    return _entry_out(entry, db.get(Worker, entry.worker_id))
