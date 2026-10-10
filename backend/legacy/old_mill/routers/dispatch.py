"""Dispatch router."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import Dispatch, DispatchRoll, DispatchStatus, NumberSequence, User
from mill.services.dispatch import confirm_dispatch

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


def _next_dispatch_no(db: Session) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == "dispatch_no").with_for_update().first()
    if seq is None:
        seq = NumberSequence(name="dispatch_no", last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"DIS-{seq.last_value:06d}"


class DispatchIn(BaseModel):
    buyer_id: int
    order_id: int
    dispatch_date: date
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None


class AddRollsIn(BaseModel):
    roll_ids: List[int]


@router.get("/")
def list_dispatches(db: Session = Depends(get_db), _=Depends(can("dispatch.read"))):
    dispatches = db.query(Dispatch).order_by(Dispatch.id.desc()).all()
    return [
        {
            "id": d.id, "doc_no": d.doc_no, "buyer": d.buyer.name,
            "dispatch_date": d.dispatch_date, "status": d.status,
            "roll_count": len(d.dispatch_rolls),
        }
        for d in dispatches
    ]


@router.post("/")
def create_dispatch(
    body: DispatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("dispatch.write")),
):
    d = Dispatch(
        doc_no=_next_dispatch_no(db),
        buyer_id=body.buyer_id,
        order_id=body.order_id,
        dispatch_date=body.dispatch_date,
        vehicle_no=body.vehicle_no,
        driver_name=body.driver_name,
        created_by=user.id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "doc_no": d.doc_no}


@router.post("/{dispatch_id}/rolls")
def add_rolls(
    dispatch_id: int,
    body: AddRollsIn,
    db: Session = Depends(get_db),
    _=Depends(can("dispatch.write")),
):
    d = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not d:
        raise HTTPException(404, "Dispatch not found")
    if d.status == DispatchStatus.confirmed:
        raise HTTPException(400, "Dispatch already confirmed")
    for roll_id in body.roll_ids:
        dr = DispatchRoll(dispatch_id=dispatch_id, roll_id=roll_id)
        db.add(dr)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Roll already on another dispatch: {e}")
    return {"ok": True}


@router.post("/{dispatch_id}/confirm")
def do_confirm(
    dispatch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(can("dispatch.write")),
):
    try:
        dispatch = confirm_dispatch(db, dispatch_id, user.id)
        db.commit()
        return {"ok": True, "doc_no": dispatch.doc_no}
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.get("/{dispatch_id}")
def get_dispatch(dispatch_id: int, db: Session = Depends(get_db), _=Depends(can("dispatch.read"))):
    d = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not d:
        raise HTTPException(404, "Dispatch not found")
    return {
        "id": d.id, "doc_no": d.doc_no, "buyer": d.buyer.name,
        "order_id": d.order_id, "dispatch_date": d.dispatch_date,
        "vehicle_no": d.vehicle_no, "driver_name": d.driver_name,
        "status": d.status,
        "rolls": [
            {
                "roll_id": dr.roll_id, "roll_no": dr.roll.roll_no,
                "length_m": dr.roll.length_cm / 100, "status": dr.roll.status,
            }
            for dr in d.dispatch_rolls
        ],
        "invoice": {"id": d.invoice.id, "doc_no": d.invoice.doc_no, "amount_paise": d.invoice.amount_paise}
        if d.invoice else None,
    }
