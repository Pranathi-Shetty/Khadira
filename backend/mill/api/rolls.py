"""Rolls router: list, create, move to store."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import Roll
from ..services import production as prod_svc
from ..services import qc as qc_svc
from .deps import Db, Params, can, paginate

router = APIRouter(prefix="/api/rolls", tags=["rolls"])


class RollIn(BaseModel):
    run_id: int
    length_cm: int = Field(gt=0)
    weight_g: int | None = None


class InspectIn(BaseModel):
    verdict: str  # passed|failed|held
    grade: str | None = None
    note: str | None = None


def _out(r: Roll) -> dict:
    return {
        "id": r.id, "roll_number": r.roll_number,
        "run_id": r.run_id, "item_id": r.item_id,
        "length_m": round(r.length_cm / 100, 2),
        "weight_g": r.weight_g, "status": r.status,
        "qc_grade": r.qc_grade,
        "created_at": r.created_at.isoformat(),
    }


@router.get("")
def list_rolls(db: Db, _: can("rolls.read"), params: Params,
               status: str | None = None) -> dict:
    stmt = select(Roll)
    if status:
        stmt = stmt.where(Roll.status == status)
    stmt = stmt.order_by(Roll.id.desc())
    return paginate(db, stmt, params, _out)


@router.post("", status_code=201)
def create_roll(body: RollIn, db: Db, user: can("rolls.write")) -> dict:
    roll = prod_svc.create_roll(db, run_id=body.run_id, length_cm=body.length_cm,
                                weight_g=body.weight_g, user_id=user.id)
    db.commit()
    db.refresh(roll)
    return _out(roll)


@router.get("/{roll_id}")
def get_roll(roll_id: int, db: Db, _: can("rolls.read")) -> dict:
    from ..services.common import DomainError
    r = db.get(Roll, roll_id)
    if r is None:
        raise DomainError("Roll not found.", 404)
    return _out(r)


@router.post("/{roll_id}/inspect")
def inspect(roll_id: int, body: InspectIn, db: Db, user: can("qc.write")) -> dict:
    roll = qc_svc.inspect_roll(db, roll_id, body.verdict, body.grade, body.note, user.id)
    db.commit()
    return _out(roll)


@router.post("/{roll_id}/store")
def to_store(roll_id: int, db: Db, user: can("rolls.write")) -> dict:
    roll = qc_svc.move_to_store(db, roll_id, user.id)
    db.commit()
    return _out(roll)
