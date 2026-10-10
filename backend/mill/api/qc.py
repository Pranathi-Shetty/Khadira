"""QC router (thin — inspect via /rolls/{id}/inspect)."""

from fastapi import APIRouter
from sqlalchemy import select

from ..models import Roll
from .deps import Db, can

router = APIRouter(prefix="/api/qc", tags=["qc"])


@router.get("/pending")
def pending_qc(db: Db, _: can("qc.read")) -> list:
    rolls = db.scalars(select(Roll).where(Roll.status.in_(["awaiting_qc", "held"]))).all()
    return [{"id": r.id, "roll_number": r.roll_number,
             "item_id": r.item_id, "status": r.status,
             "length_m": round(r.length_cm / 100, 2)} for r in rolls]
