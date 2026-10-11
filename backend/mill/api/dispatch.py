"""Dispatch router: bulk dispatch and draft->confirm lifecycle."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import Dispatch
from ..services import dispatch as svc
from ..services.common import DomainError
from .deps import Db, can
from .finance import _inv_out

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


class DispatchIn(BaseModel):
    buyer_id: int | None = None
    order_id: int | None = None
    roll_ids: list[int] | None = None
    dispatch_date: date = Field(default_factory=date.today)
    vehicle_no: str | None = None
    notes: str | None = None


class RollsIn(BaseModel):
    roll_ids: list[int] = Field(min_length=1)


@router.get("")
@router.get("/")
def list_dispatches(db: Db, _: can("dispatch.read")) -> list:
    stmt = select(Dispatch).order_by(Dispatch.id.desc())
    return [
        {
            "id": d.id,
            "dispatch_number": d.dispatch_number,
            "status": d.status,
            "order_id": d.order_id,
            "buyer_id": d.buyer_id,
            "dispatch_date": str(d.dispatch_date),
            "vehicle_no": d.vehicle_no,
            "rolls_count": len(d.rolls),
        }
        for d in db.scalars(stmt).all()
    ]


@router.get("/{dispatch_id}")
def get_dispatch(dispatch_id: int, db: Db, _: can("dispatch.read")) -> dict:
    dispatch = db.get(Dispatch, dispatch_id)
    if dispatch is None:
        raise DomainError(f"Dispatch {dispatch_id} not found.", 404)
    return {
        "id": dispatch.id,
        "dispatch_number": dispatch.dispatch_number,
        "status": dispatch.status,
        "order_id": dispatch.order_id,
        "buyer_id": dispatch.buyer_id,
        "dispatch_date": str(dispatch.dispatch_date),
        "vehicle_no": dispatch.vehicle_no,
        "notes": dispatch.notes,
        "invoice": _inv_out(dispatch.invoice) if dispatch.invoice else None,
        "rolls": [
            {
                "id": dr.roll.id,
                "roll_number": dr.roll.roll_number,
                "length_cm": dr.length_cm,
                "status": dr.roll.status,
            }
            for dr in dispatch.rolls
        ],
    }


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_or_dispatch(body: DispatchIn, db: Db, user: can("dispatch.write")) -> dict:
    if body.roll_ids is not None and len(body.roll_ids) > 0:
        # Direct atomic dispatch of rolls
        dispatch, invoice, rolls = svc.dispatch_rolls(
            db,
            roll_ids=body.roll_ids,
            dispatch_date=body.dispatch_date,
            order_id=body.order_id,
            buyer_id=body.buyer_id,
            vehicle_no=body.vehicle_no,
            notes=body.notes,
            user_id=user.id,
        )
        db.commit()
        return {
            "id": dispatch.id,
            "dispatch_id": dispatch.id,
            "dispatch_number": dispatch.dispatch_number,
            "status": dispatch.status,
            "order_id": dispatch.order_id,
            "buyer_id": dispatch.buyer_id,
            "dispatched": len(rolls),
            "invoice": _inv_out(invoice),
            "rolls": [{"id": r.id, "roll_number": r.roll_number, "status": r.status} for r in rolls],
        }
    else:
        # Create draft dispatch
        if body.order_id is None or body.buyer_id is None:
            raise DomainError("order_id and buyer_id are required for draft dispatch.", 400)
        dispatch = svc.create_dispatch_draft(
            db,
            buyer_id=body.buyer_id,
            order_id=body.order_id,
            dispatch_date=body.dispatch_date,
            vehicle_no=body.vehicle_no,
            notes=body.notes,
            user_id=user.id,
        )
        db.commit()
        return {
            "id": dispatch.id,
            "dispatch_id": dispatch.id,
            "dispatch_number": dispatch.dispatch_number,
            "status": dispatch.status,
            "order_id": dispatch.order_id,
            "buyer_id": dispatch.buyer_id,
        }


@router.post("/{dispatch_id}/rolls", status_code=200)
def add_rolls(dispatch_id: int, body: RollsIn, db: Db, user: can("dispatch.write")) -> dict:
    added = svc.add_rolls_to_dispatch(
        db,
        dispatch_id=dispatch_id,
        roll_ids=body.roll_ids,
        user_id=user.id,
    )
    db.commit()
    return {
        "added": len(added),
        "roll_ids": [r.roll_id for r in added],
    }


@router.post("/{dispatch_id}/confirm", status_code=200)
def confirm_dispatch(dispatch_id: int, db: Db, user: can("dispatch.write")) -> dict:
    dispatch, invoice = svc.confirm_dispatch(
        db,
        dispatch_id=dispatch_id,
        user_id=user.id,
    )
    db.commit()
    return {
        "id": dispatch.id,
        "status": dispatch.status,
        "invoice": _inv_out(invoice),
    }
