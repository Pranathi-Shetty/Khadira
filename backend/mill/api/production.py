"""Production router: runs, stage advance."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..models import ProductionRun
from ..services import production as svc
from .deps import Db, can

router = APIRouter(prefix="/api/production", tags=["production"])


class RunIn(BaseModel):
    machine_id: int
    order_id: int | None = None
    item_id: int


class AdvanceIn(BaseModel):
    yarn_kg: float | None = None


def _run_out(r: ProductionRun) -> dict:
    return {
        "id": r.id, "machine_id": r.machine_id,
        "order_id": r.order_id, "item_id": r.item_id,
        "current_stage": r.current_stage, "status": r.status,
        "yarn_used_kg": round((r.yarn_used_g or 0) / 1000, 3),
        "started_at": r.started_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "roll_count": len(r.rolls),
    }


@router.get("")
def list_runs(db: Db, _: can("production.read"),
              status: str | None = None) -> list:
    stmt = select(ProductionRun)
    if status:
        stmt = stmt.where(ProductionRun.status == status)
    stmt = stmt.order_by(ProductionRun.id.desc())
    return [_run_out(r) for r in db.scalars(stmt).all()]


@router.post("", status_code=201)
def start_run(body: RunIn, db: Db, user: can("production.write")) -> dict:
    run = svc.start_run(db, machine_id=body.machine_id, order_id=body.order_id,
                        item_id=body.item_id, user_id=user.id)
    db.commit()
    db.refresh(run)
    return _run_out(run)


@router.get("/{run_id}")
def get_run(run_id: int, db: Db, _: can("production.read")) -> dict:
    from ..services.common import DomainError
    r = db.get(ProductionRun, run_id)
    if r is None:
        raise DomainError("Run not found.", 404)
    return _run_out(r)


@router.post("/{run_id}/advance")
def advance(run_id: int, body: AdvanceIn, db: Db, user: can("production.write")) -> dict:
    run = svc.advance_stage(db, run_id, body.yarn_kg, user.id)
    db.commit()
    return _run_out(run)
