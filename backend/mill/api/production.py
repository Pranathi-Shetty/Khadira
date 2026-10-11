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
def list_runs(db: Db, _: can["production.read"],
              status: str | None = None) -> list:
    stmt = select(ProductionRun)
    if status:
        stmt = stmt.where(ProductionRun.status == status)
    stmt = stmt.order_by(ProductionRun.id.desc())
    return [_run_out(r) for r in db.scalars(stmt).all()]


@router.post("", status_code=201)
def start_run(body: RunIn, db: Db, user: can["production.write"]) -> dict:
    run = svc.start_run(db, machine_id=body.machine_id, order_id=body.order_id,
                        item_id=body.item_id, user_id=user.id)
    db.commit()
    db.refresh(run)
    return _run_out(run)


@router.get("/{run_id}")
def get_run(run_id: int, db: Db, _: can["production.read"]) -> dict:
    from ..services.common import DomainError
    r = db.get(ProductionRun, run_id)
    if r is None:
        raise DomainError("Run not found.", 404)
    return _run_out(r)


@router.post("/{run_id}/advance")
def advance(run_id: int, body: AdvanceIn, db: Db, user: can["production.write"]) -> dict:
    run = svc.advance_stage(db, run_id, body.yarn_kg, user.id)
    db.commit()
    return _run_out(run)


class MaterialIn(BaseModel):
    lot_id: int | None = None
    item_id: int | None = None
    qty_g: int

@router.post("/{run_id}/materials", status_code=201)
def issue_material(run_id: int, body: MaterialIn, db: Db, user: can["production.write"]) -> dict:
    if body.lot_id is not None:
        rm = svc.issue_material(db, run_id, body.lot_id, body.qty_g, user.id)
        db.commit()
        return {"id": rm.id, "run_id": rm.run_id, "lot_id": rm.lot_id, "issued_g": rm.issued_g}
    else:
        rms = svc.issue_yarn_to_run(db, run_id=run_id, qty_g=body.qty_g, item_id=body.item_id, user_id=user.id)
        db.commit()
        return {
            "run_id": run_id,
            "materials": [{"id": rm.id, "lot_id": rm.lot_id, "issued_g": rm.issued_g} for rm in rms],
            "total_issued_g": sum(rm.issued_g for rm in rms)
        }


class ReconciliationIn(BaseModel):
    planned_g: int | None = None
    consumed_g: int | None = None
    returned_g: int | None = None
    process_waste_g: int | None = None
    usable_output_cm: int | None = None
    qc_rejected_cm: int | None = None
    reason: str | None = None

def _recon_out(recon):
    return {
        "run_id": recon.run_id,
        "planned_g": recon.planned_g,
        "issued_g": recon.issued_g,
        "consumed_g": recon.consumed_g,
        "returned_g": recon.returned_g,
        "process_waste_g": recon.process_waste_g,
        "usable_output_cm": recon.usable_output_cm,
        "qc_rejected_cm": recon.qc_rejected_cm,
        "status": recon.status,
        "reason": recon.reason,
    }

@router.post("/{run_id}/reconciliation")
def save_reconciliation(run_id: int, body: ReconciliationIn, db: Db, user: can["production.write"]) -> dict:
    recon = svc.save_reconciliation(db, run_id, body.model_dump(exclude_unset=True), user.id)
    db.commit()
    return _recon_out(recon)

@router.post("/{run_id}/reconciliation/finalize")
def finalize_reconciliation(run_id: int, db: Db, user: can["production.write"]) -> dict:
    recon = svc.finalize_reconciliation(db, run_id, user.id)
    db.commit()
    return _recon_out(recon)

