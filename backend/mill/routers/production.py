"""Production runs router."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import (
    Item, MachineStatus, ProductionRun, Roll, RunStatus,
    StockMoveKind, User, YarnLot,
)
from mill.services import stock as stock_svc
from mill.services.rolls import next_roll_no, transition_roll
from mill.models import RollStatus

router = APIRouter(prefix="/api/production", tags=["production"])

RAW_STORE_LOCATION_ID = 1


class RunIn(BaseModel):
    order_id: int
    machine_id: int
    stage: str
    shift: str
    operator_id: Optional[int] = None
    yarn_lot_id: Optional[int] = None


class YarnIssueIn(BaseModel):
    grams: int


class RollCreateIn(BaseModel):
    length_cm: int
    weight_grams: Optional[int] = None
    yarn_lot_id: Optional[int] = None


@router.get("/")
def list_runs(
    order_id: Optional[int] = None,
    machine_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(can("production.read")),
):
    q = db.query(ProductionRun)
    if order_id:
        q = q.filter(ProductionRun.order_id == order_id)
    if machine_id:
        q = q.filter(ProductionRun.machine_id == machine_id)
    runs = q.order_by(ProductionRun.id.desc()).all()
    return [
        {
            "id": r.id, "order_id": r.order_id, "machine_id": r.machine_id,
            "stage": r.stage, "shift": r.shift, "status": r.status,
            "yarn_issued_grams": r.yarn_issued_grams,
            "roll_count": len(r.rolls),
            "start_time": r.start_time, "end_time": r.end_time,
        }
        for r in runs
    ]


@router.post("/")
def create_run(
    body: RunIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("production.write")),
):
    run = ProductionRun(
        order_id=body.order_id,
        machine_id=body.machine_id,
        stage=body.stage,
        shift=body.shift,
        operator_id=body.operator_id or user.id,
        yarn_lot_id=body.yarn_lot_id,
        start_time=datetime.utcnow(),
        created_by=user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id}


@router.post("/{run_id}/issue-yarn")
def issue_yarn(
    run_id: int,
    body: YarnIssueIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("production.write")),
):
    run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status != RunStatus.active:
        raise HTTPException(400, "Run is not active")

    # Get item from order's fabric and use its average cost
    item = run.order.item
    # Find yarn item linked to this fabric (approximation: use yarn_lot if set)
    if run.yarn_lot:
        yarn_item_id = run.yarn_lot.item_id
        yarn_item = db.query(Item).filter(Item.id == yarn_item_id).first()
        unit_cost = yarn_item.average_cost_paise if yarn_item else 0
    else:
        unit_cost = 0

    stock_svc.post_move(
        db,
        item_id=run.yarn_lot.item_id if run.yarn_lot else item.id,
        location_id=RAW_STORE_LOCATION_ID,
        quantity_delta=-body.grams,
        unit_cost_paise=unit_cost,
        kind=StockMoveKind.yarn_issue,
        reference_id=run.id,
        reference_type="production_run",
        user_id=user.id,
        note=f"Yarn issue for run {run.id}",
    )

    run.yarn_issued_grams += body.grams
    run.yarn_cost_paise_per_gram = unit_cost
    db.commit()
    return {"ok": True, "total_issued_grams": run.yarn_issued_grams}


@router.post("/{run_id}/rolls")
def create_roll(
    run_id: int,
    body: RollCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("production.write")),
):
    run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")

    roll_no = next_roll_no(db)
    roll = Roll(
        roll_no=roll_no,
        order_id=run.order_id,
        machine_id=run.machine_id,
        run_id=run.id,
        shift=run.shift,
        operator_id=body.operator_id if hasattr(body, "operator_id") else user.id,
        yarn_lot_id=body.yarn_lot_id or run.yarn_lot_id,
        length_cm=body.length_cm,
        weight_grams=body.weight_grams,
        status=RollStatus.produced,
    )
    db.add(roll)
    db.flush()

    # Immediately move to awaiting_qc
    from mill.models import RollEvent
    event = RollEvent(
        roll_id=roll.id,
        from_status=None,
        to_status=RollStatus.produced,
        changed_by=user.id,
        note="Roll created",
    )
    db.add(event)
    db.commit()
    db.refresh(roll)
    return {"id": roll.id, "roll_no": roll.roll_no}


@router.post("/{run_id}/complete")
def complete_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(can("production.write")),
):
    run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    run.status = RunStatus.completed
    run.end_time = datetime.utcnow()
    db.commit()
    return {"ok": True}
