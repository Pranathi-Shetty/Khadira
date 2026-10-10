"""Rolls router: status transitions, QC, lookup."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import QCResult, Roll, RollStatus, User
from mill.services.rolls import record_qc, transition_roll

router = APIRouter(prefix="/api/rolls", tags=["rolls"])


class TransitionIn(BaseModel):
    to_status: RollStatus
    note: Optional[str] = None


class QCIn(BaseModel):
    result: QCResult
    defects: Optional[list] = None
    notes: Optional[str] = None


@router.get("/")
def list_rolls(
    order_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(can("rolls.read")),
):
    q = db.query(Roll)
    if order_id:
        q = q.filter(Roll.order_id == order_id)
    if status:
        q = q.filter(Roll.status == status)
    rolls = q.order_by(Roll.id.desc()).limit(200).all()
    return [
        {
            "id": r.id, "roll_no": r.roll_no, "order_id": r.order_id,
            "machine_id": r.machine_id, "shift": r.shift,
            "length_cm": r.length_cm, "length_m": r.length_cm / 100,
            "status": r.status, "created_at": r.created_at,
        }
        for r in rolls
    ]


@router.get("/{roll_id}")
def get_roll(roll_id: int, db: Session = Depends(get_db), _=Depends(can("rolls.read"))):
    roll = db.query(Roll).filter(Roll.id == roll_id).first()
    if not roll:
        raise HTTPException(404, "Roll not found")
    return {
        "id": roll.id,
        "roll_no": roll.roll_no,
        "order_id": roll.order_id,
        "order_doc_no": roll.order.doc_no,
        "machine_id": roll.machine_id,
        "machine_name": roll.machine.name,
        "run_id": roll.run_id,
        "shift": roll.shift,
        "length_cm": roll.length_cm,
        "length_m": roll.length_cm / 100,
        "weight_grams": roll.weight_grams,
        "status": roll.status,
        "events": [
            {"from": e.from_status, "to": e.to_status, "note": e.note, "at": e.created_at}
            for e in sorted(roll.events, key=lambda x: x.created_at)
        ],
        "qc_inspections": [
            {"result": q.result, "defects": q.defects, "notes": q.notes, "at": q.inspected_at}
            for q in roll.qc_inspections
        ],
    }


@router.get("/by-no/{roll_no}")
def get_roll_by_no(roll_no: str, db: Session = Depends(get_db), _=Depends(can("rolls.read"))):
    roll = db.query(Roll).filter(Roll.roll_no == roll_no).first()
    if not roll:
        raise HTTPException(404, "Roll not found")
    return get_roll(roll.id, db, _)


@router.post("/{roll_id}/transition")
def do_transition(
    roll_id: int,
    body: TransitionIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("rolls.write")),
):
    try:
        roll = transition_roll(db, roll_id, body.to_status, user.id, body.note)
        db.commit()
        return {"ok": True, "status": roll.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{roll_id}/qc")
def do_qc(
    roll_id: int,
    body: QCIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("qc.write")),
):
    try:
        inspection = record_qc(
            db,
            roll_id=roll_id,
            inspector_id=user.id,
            result=body.result,
            defects=body.defects,
            notes=body.notes,
        )
        db.commit()
        return {"ok": True, "inspection_id": inspection.id}
    except ValueError as e:
        raise HTTPException(400, str(e))
