"""Machines router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import Machine, MachineStatus, MachineStatusLog, MachineType, User

router = APIRouter(prefix="/api/machines", tags=["machines"])


class MachineIn(BaseModel):
    code: str
    name: str
    machine_type: MachineType
    notes: Optional[str] = None


class StatusChangeIn(BaseModel):
    to_status: MachineStatus
    note: Optional[str] = None


@router.get("/")
def list_machines(db: Session = Depends(get_db), _=Depends(can("machines.read"))):
    machines = db.query(Machine).all()
    return [
        {
            "id": m.id, "code": m.code, "name": m.name,
            "machine_type": m.machine_type, "status": m.status,
        }
        for m in machines
    ]


@router.post("/")
def create_machine(
    body: MachineIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("machines.write")),
):
    m = Machine(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "code": m.code}


@router.post("/{machine_id}/status")
def change_status(
    machine_id: int,
    body: StatusChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("machines.write")),
):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(404, "Machine not found")
    log = MachineStatusLog(
        machine_id=machine_id,
        from_status=machine.status,
        to_status=body.to_status,
        changed_by=user.id,
        note=body.note,
    )
    db.add(log)
    machine.status = body.to_status
    db.commit()
    return {"ok": True, "status": machine.status}


@router.get("/{machine_id}/log")
def machine_log(machine_id: int, db: Session = Depends(get_db), _=Depends(can("machines.read"))):
    logs = (
        db.query(MachineStatusLog)
        .filter(MachineStatusLog.machine_id == machine_id)
        .order_by(MachineStatusLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "from_status": l.from_status, "to_status": l.to_status,
            "note": l.note, "created_at": l.created_at,
        }
        for l in logs
    ]
