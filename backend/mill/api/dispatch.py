"""Dispatch router: bulk dispatch of in-store rolls."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services import dispatch as svc
from .deps import Db, can

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


class DispatchIn(BaseModel):
    roll_ids: list[int] = Field(min_length=1)
    dispatch_date: date
    buyer_id: int | None = None
    vehicle_no: str | None = None
    notes: str | None = None


@router.post("", status_code=201)
def dispatch_rolls(body: DispatchIn, db: Db, user: can("dispatch.write")) -> dict:
    rolls = svc.dispatch_rolls(
        db, roll_ids=body.roll_ids,
        dispatch_date=body.dispatch_date,
        buyer_id=body.buyer_id,
        vehicle_no=body.vehicle_no,
        notes=body.notes,
        user_id=user.id,
    )
    db.commit()
    return {
        "dispatched": len(rolls),
        "rolls": [{"id": r.id, "roll_number": r.roll_number, "status": r.status} for r in rolls],
    }
