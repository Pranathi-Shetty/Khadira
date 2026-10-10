"""Machines router."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..models import Machine
from ..services import machines as svc
from .deps import Db, can

router = APIRouter(prefix="/api/machines", tags=["machines"])


class MachineIn(BaseModel):
    code: str
    name: str
    machine_type: str  # spinning|weaving|dyeing


def _out(m: Machine) -> dict:
    return {"id": m.id, "code": m.code, "name": m.name,
            "machine_type": m.machine_type, "is_active": m.is_active}


@router.get("")
def list_machines(db: Db, _: can["machines.read"]) -> list:
    return [_out(m) for m in db.scalars(select(Machine).where(Machine.is_active.is_(True))).all()]


@router.post("", status_code=201)
def create_machine(body: MachineIn, db: Db, user: can["machines.write"]) -> dict:
    m = svc.create_machine(db, code=body.code, name=body.name,
                           machine_type=body.machine_type, user_id=user.id)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.get("/{machine_id}")
def get_machine(machine_id: int, db: Db, _: can["machines.read"]) -> dict:
    from ..services.common import DomainError
    m = db.get(Machine, machine_id)
    if m is None:
        raise DomainError("Machine not found.", 404)
    return _out(m)

class DowntimeIn(BaseModel):
    reason: str
    description: str | None = None
    run_id: int | None = None

class ResolutionIn(BaseModel):
    resolution: str

@router.post("/{machine_id}/downtime", status_code=201)
def log_downtime(machine_id: int, body: DowntimeIn, db: Db, user: can["machines.write"]) -> dict:
    dt = svc.log_downtime(db, machine_id=machine_id, reason=body.reason,
                          description=body.description, run_id=body.run_id, user_id=user.id)
    db.commit()
    return {"id": dt.id, "machine_id": dt.machine_id, "start_time": dt.start_time.isoformat()}

@router.post("/downtime/{downtime_id}/resolve")
def resolve_downtime(downtime_id: int, body: ResolutionIn, db: Db, user: can["machines.write"]) -> dict:
    dt = svc.resolve_downtime(db, downtime_id=downtime_id, resolution=body.resolution, user_id=user.id)
    db.commit()
    return {"id": dt.id, "machine_id": dt.machine_id, "end_time": dt.end_time.isoformat()}

